import os
import sys
from unittest.mock import MagicMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
# The Lambdas import aws_errors from their layer, as they do in AWS
sys.path.insert(0, os.path.join(ROOT, 'functions', 'layers', 'aws_errors', 'python'))

# Module-level boto3 clients are created at import; no call is made, but a region is needed
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-north-1')
os.environ.setdefault('CROSS_ACCOUNT_ROLE', 'AWSControlTowerExecution')
os.environ.setdefault('REGIONS', "['eu-north-1']")
os.environ.setdefault('EMAIL_SIGNEE', 'Example')
os.environ.setdefault('SEND_EMAIL', 'Yes')
os.environ.setdefault('EMAIL_SENDER', 'sender@example.com')
os.environ.setdefault('EMAIL_CC', '')
os.environ.setdefault('EMAIL_BCC', '')
os.environ.setdefault('EMAIL_RETURN_PATH', 'bounces@example.com')


@pytest.fixture(autouse=True)
def mock_aws_services():
    """Prevents ALL AWS API calls: every boto3 client the Lambdas create is a MagicMock."""
    with patch('boto3.client', side_effect=lambda *args, **kwargs: MagicMock(name=f'client:{args[0]}')):
        yield
