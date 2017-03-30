from __future__ import print_function

import sys
import argparse
import boto3
import logging
import ec2_settings
import spot_instance
import jsondb

MAX_ALLOWED_BID = 1.00

def _get_client(region_name):
  return boto3.client('ec2', region_name=region_name)

def _print_failed(hosts):
  print("failed to request spot instance for all regions.", file=sys.stderr)
  
  if hosts and len(hosts) > 0:
    print("already started instances:", file=sys.stderr)
    for rec in hosts:
      print(rec['host'], file=sys.stderr)

def _print_done(hosts):
  for rec in hosts:
    print(rec['host'])

def _is_instance_running(client, iid):
  resp = client.describe_instance_status(DryRun=False, InstanceIds=[iid])
  if 'InstanceStatuses' in resp and \
    len(resp['InstanceStatuses']) == 1:
    rec = resp['InstanceStatuses'][0]
    return rec['InstanceState']['Name'] != 'terminated'
  else:
    return False

def create_or_insert_cluster(mode, cluster_name, regions, price, 
  instance_type, group_name):
  assert mode == 'insert' or mode == 'create', 'invalid mode value'

  op_failed = False
  hosts = []
  for cur_region in regions:
    if op_failed:
      break

    client = _get_client(cur_region)
    zones = spot_instance.availability_zones(client)
    if not zones:
      logging.warn("no available zone for region " + cur_region)
    
    secgrp_id = spot_instance.get_security_group_id(client, group_name)
    if secgrp_id is None:
      logging.warning("failed to get the security group id for region " + \
        cur_region)
      raise RuntimeError("group id need to be set on amazon ec2")

    secgrp_name = ec2_settings.security_group_name
    ami = ec2_settings.ami_name[cur_region]
    spot_price = price
    instance_type = instance_type
    
    requested = False 
    for cur_az in zones:
      logging.info("Processing " + cur_region + ", az " + cur_az)
      logging.debug("ami:" + ami + ",az:" + cur_az + ",grp name:" + \
        secgrp_name + ",grp id:" + secgrp_id + ",price:" + spot_price + \
        "type:" + instance_type)
      instance_id, host, failed, reason, timeout = \
        spot_instance.request_ec2_spot_instance(client, ami, cur_az, secgrp_name,\
          secgrp_id, spot_price, instance_type)
   
      if failed and reason == 'capacity-not-available':
        logging.warning('capacity-not-available at ' + cur_az)
        continue
      elif failed:
        logging.warning('failed to request spot instance')
        op_failed = True
        break
      elif timeout:
        logging.warning('timeout, manual intervention required')
        op_failed = True
        break
      else:
        requested = True
        host_rec = {
          "region": cur_region,
          "az": cur_az,
          "host": host,
          "type": instance_type,
          "instance_id": instance_id,
        }
        hosts.append(host_rec)
        jsondb.insert_into_json_db(cluster_name, [host_rec], False)
        break

    if not requested:
      logging.warn("failed to request instance for region " + cur_region)

  if op_failed:
    _print_failed(hosts)
    sys.exit(1)
  else:
    _print_done(hosts)

  jsondb.insert_into_json_db(cluster_name, [], True)

def terminate_cluster(cluster_name):
  if not jsondb.exist(cluster_name):
    raise RuntimeError("cluster " + cluster_name + " does not exist.")

  db_rec = jsondb.read_json_db(cluster_name)
  if db_rec['cluster_name'] != cluster_name:
    raise RuntimeError('db.cluster_name != cluster name')

  for cur_member in db_rec["cluster_members"]:
    region = cur_member["region"]
    client = _get_client(region)
    iid = cur_member['instance_id']
    host = cur_member['host']

    if not _is_instance_running(client, iid):
      logging.info("" + iid + " is not running, skipped")
      continue

    logging.info("terminating " + iid + ", from region " + region)
    failed = True
    resp = client.terminate_instances(DryRun=False, InstanceIds=[iid])
    if 'TerminatingInstances' in resp:
      if len(resp['TerminatingInstances']) and \
        resp['TerminatingInstances'][0]['InstanceId'] == iid:
        failed = False
    
    if failed:
      logging.warning("failed to terminate " + iid + " host " + host)

  jsondb.delete_cluster(cluster_name)

def list_cluster(cluster_name):
  if not jsondb.exist(cluster_name):
    logging.warning("json db file does not exist")
    return
  
  db_rec = jsondb.read_json_db(cluster_name)
  if db_rec['cluster_name'] != cluster_name:
    raise RuntimeError('db.cluster_name != cluster name')

  for cur_member in db_rec["cluster_members"]:
    region = cur_member["region"]
    client = _get_client(region)
    iid = cur_member['instance_id']
    host = cur_member['host']

    logging.info("listing " + iid + ", from region " + region)
    resp = client.describe_instance_status(DryRun=False, InstanceIds=[iid])
    if 'InstanceStatuses' in resp and \
      len(resp['InstanceStatuses']) == 1:
      rec = resp['InstanceStatuses'][0]
      print("%s, %s, %s" % (rec['InstanceId'], host, rec['InstanceState']['Name']))

def main():
  parser = argparse.ArgumentParser(
    description='Manage EC2 spot instances based small cluster')
  parser.add_argument(
    '--cluster-name', 
    dest='cluster_name', 
    type=str,
    help="name of the cluster, it will also be used as the json filename")
  parser.add_argument(
    '--region',
    dest='region',
    type=str,
    help="a list of interested region list separated by comma")
  parser.add_argument(
    '--security-group',
    dest='security_group',
    type=str,
    default="raft-sg",
    help="the security group name to use")
  parser.add_argument(
    '--instance-type',
    dest='instance_type',
    type=str,
    default="c3.medium",
    help="ec2 instance type")
  parser.add_argument(
    '--price',
    dest='price',
    type=str,
    default="1.00",
    help="max bid price, e.g. 0.7")
  parser.add_argument(
    '--mode',
    dest='mode',
    choices=['create', 'insert', 'terminate', 'list'],
    default='insert',
    help="whether to create a cluster or insert new instances")
  args = parser.parse_args()

  logging.basicConfig(level=logging.WARN)

  if not jsondb.is_valid_cluster_name(args.cluster_name):
    raise RuntimeError("invalid cluster name, only [0-9a-zA-Z] are allowed")
  
  if not args.region:
    regions = ec2_settings.regions
  else:
    regions = [x.strip().lower() for x in args.region.split(',')]

  if args.price:
    try:
      float_price = float(args.price)
      if float_price > MAX_ALLOWED_BID:
        raise RuntimeError("bid price is too high") 
    except:
      raise

  if args.mode == 'list' or args.mode == 'terminate':
    if args.region:
      raise RuntimeError("list/terminate/region can not be specified together")

  if args.mode == 'insert' or args.mode == 'create':
    if args.mode == 'create' and jsondb.exist(args.cluster_name):
      raise RuntimeError("specified cluster already exist in jsondb")
    create_or_insert_cluster(args.mode, args.cluster_name, regions, 
      args.price, args.instance_type, args.security_group)
  elif args.mode == 'list':
    list_cluster(args.cluster_name)
  elif args.mode == 'terminate':
    terminate_cluster(args.cluster_name) 
  else:
    raise RuntimeError("not suppose to reach here.")

if __name__ == '__main__':
  main()
