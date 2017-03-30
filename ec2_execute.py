#!/usr/bin/env python

from __future__ import print_function

import argparse
import jsondb
import commands
from multiprocessing import Pool

def thread_main(input_cmd):
  cmd = input_cmd[0]
  host = input_cmd[1]
  
  ret = commands.getstatusoutput(cmd)
  return host, ret[0], ret[1]

def get_ssh_cmd(target_host, forward_host, cmd):
  cmd_list = ["ssh"]
  
  if forward_host:
    proxy_cmd = r'ProxyCommand="ssh -W %h:%p ' + forward_host + '"'
    cmd_list = cmd_list + ["-o", proxy_cmd]
  
  host_str = 'ubuntu@%s' % target_host
  cmd_list = cmd_list + [host_str] + ['"%s"' % cmd]
  
  return ' '.join(cmd_list)

def get_scp_to_cmd(target_host, forward_host, localfile):
  cmd_list = ["scp"]
  
  if forward_host:
    proxy_cmd = r'ProxyCommand="ssh -W %h:%p ' + forward_host + '"'
    cmd_list = cmd_list + ["-o", proxy_cmd]
  
  cmd_list = cmd_list + [localfile]
  host_str = 'ubuntu@%s:' % target_host
  cmd_list = cmd_list + [host_str]

  return ' '.join(cmd_list)

def main():
  parser = argparse.ArgumentParser(
    description='Parall excution on ec2 nodes')
  parser.add_argument(
    '--cluster-name', 
    dest='cluster_name',
    type=str,
    help="name of the cluster")
  parser.add_argument(
    '--cmd',
    dest='cmd',
    type=str,
    help="command to execute")
  parser.add_argument(
    '--copy-to',
    dest='copy_to',
    type=str,
    help="the local file to be copied to remotes")
  parser.add_argument(
    '--forward-host',
    dest="forward_host",
    type=str,
    help="the ssh -W forward host to use")
  args = parser.parse_args()

  if not args.cluster_name:
    raise RuntimeError("cluster name can not be empty")
  if args.cmd and args.copy_to:
    raise RuntimeError("cmd and copy_to can not be used together")
  if not args.cmd and not args.copy_to:
    raise RuntimeError("has to specify one action")

  input_cmd_list = []
  db_rec = jsondb.read_json_db(args.cluster_name)
  for cur_member in db_rec['cluster_members']:
    host = cur_member['host']

    if args.cmd:
      cur_cmd = get_ssh_cmd(host, args.forward_host, args.cmd)
    elif args.copy_to:
      cur_cmd = get_scp_to_cmd(host, args.forward_host, args.copy_to)
    else:
      raise RuntimeError("not suppose to reach here")

    input_cmd_list.append((cur_cmd, host))
    print(cur_cmd)

  thread_pool = Pool(len(input_cmd_list))
  results = thread_pool.map(thread_main, input_cmd_list)
  for rec in results:
    host = rec[0]
    code = rec[1]
    output = rec[2]
   
    print("->%d, %s" % (code, host)) 
    if output:
      output = output.strip()
      if output:
        print('## Output from %s' % host)
        print(output)

if __name__ == '__main__':
  main()
