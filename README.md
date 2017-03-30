# Amazon EC2 spot instance tools

## About

This is a lightweight toolset designed to manage small clusters using Amazon EC2 spot instances.

## Install

```
sudo pip install boto3
git clone https://github.com/distributed-sys/ec2tools
``` 

## Examples

Create a small cluster using EC2 Spot Instance type c3.large, one from each of the following regions:
* us-west-1
* us-east-1
* eu-west-1

```
python manage_cluster.py --mode insert --cluster-name test1 \
--region us-west-1,us-east-1,eu-west-1 --instance-type c3.large --security-group my-sg
```

Once completed, the details will be recorded into a local json file named test1.json. You can now list the details:
```
python manage_cluster.py --mode list --cluster-name test1
```

You can now use these nodes to run your applications. Once done and no longer required, you can terminate all nodes.
```
python manage_cluster.py --mode terminate --cluster-name test1
```

## Assumptions
* You have the required AWS credentials configured.
* There is one VPC (default one) in each region.
