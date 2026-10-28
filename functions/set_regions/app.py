import os
import json
from aws_errors import transient_aws_errors

# Assuming REGIONS is a string that might use single quotes, e.g., "['eu-north-1', 'eu-west-2']"
REGIONS = os.environ['REGIONS']

@transient_aws_errors
def lambda_handler(_data, _context):
    # Replace single quotes with double quotes
    json_regions = REGIONS.replace("'", '"')
    
    # Parse the JSON string into a Python list
    result = json.loads(json_regions)
    return result
