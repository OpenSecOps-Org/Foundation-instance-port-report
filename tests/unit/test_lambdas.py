"""
The Lambdas that call AWS: throttling and other transient AWS errors leave them as AWSTransientError, which
the state machine retries. Other errors keep their own name and are not retried.
"""

from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from aws_errors import AWSTransientError
from functions.get_organization_account_list import app as get_organization_account_list
from functions.scan_regional_instances import app as scan_regional_instances
from functions.send_email import app as send_email

MEMBER = '222222222222'


def client_error(code, status=400):
    return botocore.exceptions.ClientError(
        {'Error': {'Code': code, 'Message': code}, 'ResponseMetadata': {'HTTPStatusCode': status}}, 'op')


DENIED = client_error('AccessDeniedException', 403)


# ---------------------------------------------------------------------------

def org_client(error=None):
    client = MagicMock()
    pages = client.get_paginator.return_value.paginate
    if error:
        pages.side_effect = error
    else:
        pages.return_value = [{'Accounts': [{'Id': MEMBER, 'Status': 'ACTIVE', 'JoinedTimestamp': 'x'},
                                            {'Id': '333333333333', 'Status': 'SUSPENDED', 'JoinedTimestamp': 'x'}]}]
    return client


def test_lists_the_active_accounts():
    with patch.object(get_organization_account_list, 'client', org_client()):
        assert get_organization_account_list.lambda_handler({}, None) == [{'Id': MEMBER, 'Status': 'ACTIVE'}]


@pytest.mark.parametrize('error, transient', [(client_error('TooManyRequestsException'), True), (DENIED, False)])
def test_account_listing_errors(error, transient):
    with patch.object(get_organization_account_list, 'client', org_client(error)):
        with pytest.raises(botocore.exceptions.ClientError if not transient else AWSTransientError) as raised:
            get_organization_account_list.lambda_handler({}, None)
    assert isinstance(raised.value, AWSTransientError) == transient


# ---------------------------------------------------------------------------

def ec2_client():
    ec2 = MagicMock()
    ec2.get_paginator.return_value.paginate.return_value = [{'Reservations': [{'Instances': [
        {'InstanceId': 'i-1', 'SecurityGroups': [{'GroupId': 'sg-1', 'GroupName': 'web'}]}]}]}]
    ec2.describe_security_groups.return_value = {'SecurityGroups': [{'Description': 'web', 'IpPermissions': []}]}
    return ec2


def scan(ec2, assume_role_error=None):
    sts = MagicMock()
    if assume_role_error:
        sts.assume_role.side_effect = assume_role_error
    else:
        sts.assume_role.return_value = {'Credentials': {'AccessKeyId': 'a', 'SecretAccessKey': 'b',
                                                        'SessionToken': 'c'}}
    with patch.object(scan_regional_instances, 'sts_client', sts), \
            patch.object(scan_regional_instances.boto3, 'client', return_value=ec2):
        return scan_regional_instances.lambda_handler(
            {'Account': {'Id': MEMBER, 'Name': 'member'}, 'Region': 'eu-north-1'}, None)


def test_scans_the_instances():
    assert scan(ec2_client())['Instances']['i-1']['SecurityGroups'] == ['sg-1']


def test_a_throttled_instance_listing_is_retried():
    ec2 = ec2_client()
    ec2.get_paginator.return_value.paginate.side_effect = client_error('RequestLimitExceeded', 503)
    with pytest.raises(AWSTransientError):
        scan(ec2)


def test_a_throttled_security_group_lookup_is_retried():
    ec2 = ec2_client()
    ec2.describe_security_groups.side_effect = client_error('RequestLimitExceeded', 503)
    with pytest.raises(AWSTransientError):
        scan(ec2)


def test_a_throttled_role_assumption_is_retried():
    with pytest.raises(AWSTransientError):
        scan(ec2_client(), assume_role_error=client_error('Throttling'))


def test_a_refused_scan_keeps_its_own_name():
    ec2 = ec2_client()
    ec2.describe_security_groups.side_effect = client_error('UnauthorizedOperation', 403)
    with pytest.raises(botocore.exceptions.ClientError) as raised:
        scan(ec2)
    assert not isinstance(raised.value, AWSTransientError)


# ---------------------------------------------------------------------------

EMAIL = {'Recipient': 'a@example.com', 'Subject': 'Report', 'Body': '<p>x</p>', 'Html': True}


def test_sends_the_report():
    ses = MagicMock()
    with patch.object(send_email, 'client', ses):
        send_email.lambda_handler(dict(EMAIL), None)
    assert ses.send_email.call_args.kwargs['Destination']['ToAddresses'] == ['a@example.com']


@pytest.mark.parametrize('error, transient', [(client_error('Throttling'), True),
                                              (client_error('MessageRejected'), False)])
def test_email_errors(error, transient):
    ses = MagicMock()
    ses.send_email.side_effect = error
    with patch.object(send_email, 'client', ses):
        with pytest.raises(botocore.exceptions.ClientError if not transient else AWSTransientError) as raised:
            send_email.lambda_handler(dict(EMAIL), None)
    assert isinstance(raised.value, AWSTransientError) == transient
