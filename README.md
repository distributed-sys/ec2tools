# Amazon EC2 spot instance tools

## About

This is a python package for managing Amazon EC2 spot instances based small clusters.

## Install

```
sudo pip install boto3
git clone https://github.com/distributed-sys/ec2tools
``` 

## Examples

Create a 3-nodes cluster using EC2 Spot Instance type c3.large, one from each of the following regions:
* us-west-1
* us-east-1
* eu-west-1

```
python manage_cluster.py --mode insert --cluster-name test1 \
--region us-west-1,us-east-1,eu-west-1 --instance-type c3.large --security-group my-sg
```

Once completed, details of the created cluster will be recorded into a local json file named test1.json. You can now list the details:
```
python manage_cluster.py --mode list --cluster-name test1
```

Once done with the created cluster, terminate all nodes - 
```
python manage_cluster.py --mode terminate --cluster-name test1
```

## Assumptions
* You have the required AWS credentials configured.
* There is one VPC (default one) in each region.
