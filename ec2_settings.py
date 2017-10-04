# what regions to use
regions = ['us-west-1', 'us-west-2', 'us-east-1', 'ap-southeast-2']

# Ubuntu 16.04LTS ebs paravirtual
ami_name = {
  "us-west-2": "ami-20c04f40",
  "us-east-1": "ami-2657f630",
  "us-west-1": "ami-2d5c6d4d",
  "eu-west-1": "ami-405f7226",
  "ap-northeast-1": "ami-8422ebe2",
  'ap-southeast-2': "ami-391ff95b",
}

security_group_name = "raft-sg"

for cur_region in regions:
  if cur_region not in ami_name:
    raise RuntimeError("incomplete ami_name dict")
