#!/usr/bin/env python3
import argparse
import os
import pickle
import tempfile

import boto3
from prettytable import PrettyTable

parser = argparse.ArgumentParser(description='Lookup AWS Resources')
parser.add_argument('--force', required=False, action="store_true")
parser.add_argument('name', nargs="?", default=None)
argparse = parser.parse_args()


def cachedresponse(func):
    def cached_request_func():
        temp_dir = tempfile.gettempdir()
        temp_cache = os.path.join(temp_dir, 'awsquery.{}.pickle'.format(func.__name__))
        if os.path.exists(temp_cache) and argparse.force is False:
            with open(temp_cache, 'rb') as cache_file:
                response_cache = pickle.load(cache_file)
        else:
            with open(temp_cache, 'wb') as cache_file:
                response_cache = func()
                pickle.dump(response_cache, cache_file)

        return response_cache

    return cached_request_func


@cachedresponse
def get_ec2():
    instances = list()
    ec2 = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]

    for region in regions:
        ec2_region = boto3.client('ec2', region_name=region)
        ec2_paginator = ec2_region.get_paginator('describe_instances')
        ec2_page_iterator = ec2_paginator.paginate()

        for page in ec2_page_iterator:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    if instance['State']['Name'] != 'running':
                        continue

                    name = [instance_item['Value'] for instance_item in instance['Tags'] if instance_item['Key'] == 'Name'][0]

                    instances.append((
                        name,
                        instance['PrivateIpAddress'],
                        instance['InstanceType']
                    ))

    return instances


@cachedresponse
def get_rds():
    instances = list()
    ec2 = boto3.client('ec2')
    regions = [region['RegionName'] for region in ec2.describe_regions()['Regions']]

    for region in regions:
        rds_region = boto3.client('rds', region_name=region)
        rds_paginator = rds_region.get_paginator('describe_db_instances')
        rds_page_iterator = rds_paginator.paginate()

        for page in rds_page_iterator:
            for instance in page['DBInstances']:
                instances.append((
                    instance['DBInstanceIdentifier'],
                    instance['Endpoint']['Address'],
                    instance['EngineVersion']
                ))

    return instances



ec2_list = get_ec2()
rds_list = get_rds()

instance_list = ec2_list + rds_list
instance_list_filtered = list()

if argparse.name is not None:
    for item in instance_list:
        if item[0].lower().find(argparse.name) >= 0:
            instance_list_filtered.append(item)

else:
    instance_list_filtered = instance_list

table = PrettyTable()
table.field_names = ['Name', 'IP', 'State']
table.sortby = 'Name'
table.align = 'l'
table.add_rows(instance_list_filtered)
print(table)
