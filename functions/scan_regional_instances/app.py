import boto3
import os

CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']

sts_client = boto3.client('sts')


def lambda_handler(data, _context):
    print(data)

    account_id = data['Account']['Id']
    account_name = data['Account']['Name']
    region = data['Region']

    ec2 = get_client('ec2', account_id, region, role=CROSS_ACCOUNT_ROLE)

    paginator = ec2.get_paginator('describe_instances')
    page_iterator = paginator.paginate()

    instances = {}
    security_groups = {}

    for page in page_iterator:
        if page['Reservations'] != []:
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    record_instance(instance, instances)
                    record_security_group(ec2, instance, security_groups)

    if instances == {}:
        print(f"Account {account_id} has no EC2 instances in {region}.")
        return False

    security_groups = sort_security_groups(security_groups)
    for s_g in security_groups:
        print(s_g)

    return {
        "AccountId": account_id,
        "AccountName": account_name,
        "Region": region,
        "Instances": instances,
        "SecurityGroups": security_groups
    }


def record_instance(instance, instances):
    instance_id = instance['InstanceId']
    instance_name = next(
        (x['Value'] for x in instance.get('Tags', []) if x['Key'] == 'Name'), '')
    instances[instance_id] = {
        "Name": instance_name,
        "SecurityGroups": [d['GroupId'] for d in instance['SecurityGroups']],
        "PrivateIp": instance.get('PrivateIpAddress', False),
        "PublicIp": instance.get('PublicIpAddress', False)
    }
    print(f"{instance_id}: {instances[instance_id]}")


def record_security_group(ec2, instance, security_groups):
    instance_id = instance['InstanceId']
    for item in instance['SecurityGroups']:
        group_id = item['GroupId']
        group_name = item['GroupName']
        if not security_groups.get(group_id):
            desc, ingress = get_security_group_data(ec2, group_id)
            security_groups[group_id] = {
                "Name": group_name,
                "Description": desc,
                "IpPermissions": ingress,
                "Instances": []
            }
        security_groups[group_id]['Instances'].append(instance_id)


def get_security_group_data(ec2, group_id):
    response = ec2.describe_security_groups(GroupIds=[group_id])
    data = response['SecurityGroups'][0]
    desc = data.get('Description')
    ip_permissions = data.get('IpPermissions')
    ip_permissions = sorted(
        ip_permissions, key=lambda k: k.get('FromPort', -1))
    return desc, ip_permissions


def sort_security_groups(security_groups):
    unsorted = list(security_groups.items())
    return sorted(unsorted, key=lambda k: len(k[1]['Instances']), reverse=True)


def reformat_security_groups(sg_list):
    result = {}
    for item in sg_list:
        result[item['GroupId']] = item['GroupName']
    return result


def get_client(client_type, account_id, region, role):
    other_session = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName=f"cross_acct_lambda_session_{account_id}"
    )
    access_key = other_session['Credentials']['AccessKeyId']
    secret_key = other_session['Credentials']['SecretAccessKey']
    session_token = other_session['Credentials']['SessionToken']
    return boto3.client(
        client_type,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name=region
    )
