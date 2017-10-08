import os
import boto3
from datetime import datetime
from dateutil import tz
import local_proxy

def _to_local_time(utc_time):
    to_zone = tz.tzlocal()
    return utc_time.astimezone(to_zone)

regions = ['us-west-1', 'us-west-2', 'us-east-1', 'ap-northeast-1']
for curRegion in regions:
    ec2 = boto3.client('ec2', region_name = curRegion)
    response = ec2.describe_spot_price_history(
        InstanceTypes =['i3.16xlarge'],
        ProductDescriptions = ['Linux/UNIX'] 
    )
    
    print curRegion
    for cur_rec in response['SpotPriceHistory'][:10]:
        spot_price = cur_rec['SpotPrice']
        local_time = _to_local_time(cur_rec['Timestamp'])
        print local_time, spot_price
