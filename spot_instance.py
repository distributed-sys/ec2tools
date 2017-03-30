import boto3
import time
import logging

_pending_status_code = [
  'pending-evaluation',
  'pending-fulfillment'
]

_fullfilled_status_code = [
  'fulfilled'
]

def get_security_group_id(client, group_name):
  resp = client.describe_security_groups(DryRun=False, GroupNames=[group_name])
  if 'SecurityGroups' in resp and resp['SecurityGroups']:
    return resp['SecurityGroups'][0]['GroupId']
  else:
    return None

# return all available availability zones
def availability_zones(client):
  zone_names = []
  resp = client.describe_availability_zones(DryRun=False)
  if 'AvailabilityZones' in resp:
    for cur_az in resp['AvailabilityZones']:
      if cur_az['State'] == 'available':
        zone_names.append(cur_az['ZoneName'])
  
  return zone_names

# return a tuple of (instance_id, instance_public_dns_name, failed, 
# failed_reason, timeout)
def request_ec2_spot_instance(client, image_id, availability_zone, 
    security_group_name, security_group_id, spot_price, instance_type):
  response = client.request_spot_instances(
    DryRun=False,
    SpotPrice=spot_price,
    InstanceCount=1,
    LaunchSpecification = {
        'ImageId': image_id,
        'KeyName': 'id_rsa',
        'SecurityGroups': [security_group_name],
        'InstanceType': instance_type,
        'Placement': {'AvailabilityZone': availability_zone},
        'SecurityGroupIds': [security_group_id]
    }
  )

  failed_reason = None
  spot_instreq_id = response['SpotInstanceRequests'][0]['SpotInstanceRequestId']
  instance_id = None
  max_wait = 180
  # wait for the status to become fulfilled
  while max_wait > 0:
    response =  client.describe_spot_instance_requests(DryRun=False,
        SpotInstanceRequestIds=[spot_instreq_id])
    
    state = response['SpotInstanceRequests'][0]['State']
    logging.info("state:" + state)
    if state not in ['open', 'active']:
      logging.warning('state not in [open, active]')
      return instance_id, None, True, failed_reason, False   
    status_code = response['SpotInstanceRequests'][0]['Status']['Code']
    logging.info("status_code:" + status_code)
    if status_code in _fullfilled_status_code:
      instance_id = response['SpotInstanceRequests'][0]['InstanceId']
      break
    elif status_code in _pending_status_code:
      time.sleep(1)
      max_wait -= 1
      continue
    else:
      # worth to try the next availability zone
      if status_code == 'capacity-not-availably':
        failed_reason = 'capacity-not-availably'
      logging.warning('failed status code ' + status_code)
      return instance_id, None, True, failed_reason, False

  if instance_id is None:
    logging.warning('not fullfilled before timeout')
    return instance_id, None, False, failed_reason, True

  # start the instance
  max_wait = 90
  while max_wait > 0:
    # get public dns name
    response = client.describe_instances(DryRun=False, 
      InstanceIds=[instance_id])
    
    state_code = response['Reservations'][0]['Instances'][0]['State']['Code']
    logging.info("instance state code:" + str(state_code))
    # status_code == 16  --> running
    if state_code == 16:
      dns = response['Reservations'][0]['Instances'][0]['PublicDnsName']
      return instance_id, dns, False, failed_reason, False
    elif state_code == 0 or status_code == 256:
      max_wait -= 1
      time.sleep(1)
    else:
      # bad state
      logging.warning("unknown instance status code " + state_code)
      return instance_id, None, True, failed_reason, False
  
  logging.warning('instance not in the running state before timeout')
  return instance_id, None, False, failed_reason, True
