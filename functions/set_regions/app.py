import os

REGIONS = os.environ['REGIONS']


def lambda_handler(_data, _context):

    result = REGIONS.split(',')
    return result
