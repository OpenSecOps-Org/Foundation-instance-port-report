import os
import json

# Assuming REGIONS is a string that might use single quotes, e.g., "['eu-north-1', 'eu-west-2']"
REGIONS = os.environ['REGIONS']

def lambda_handler(_data, _context):
    # Replace single quotes with double quotes
    json_regions = REGIONS.replace("'", '"')
    
    # Parse the JSON string into a Python list
    result = json.loads(json_regions)
    return result
