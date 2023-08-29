import boto3

client = boto3.client('organizations')


def lambda_handler(_data, _context):

    paginator = client.get_paginator('list_accounts')
    account_iterator = paginator.paginate()

    result = []
    for accounts in account_iterator:
        for account in accounts['Accounts']:
            if account['Status'] == 'ACTIVE':
                tidied = account.copy()
                tidied.pop('JoinedTimestamp')
                result.append(tidied)

    return sorted(result, key=lambda k: k['Id'])
