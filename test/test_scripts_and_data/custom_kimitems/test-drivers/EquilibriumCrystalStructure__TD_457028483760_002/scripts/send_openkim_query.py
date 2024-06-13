import json
import requests

def send_openkim_query(params, endpoint):
    """
    Convert all parameters (which are python objects) to JSON strings
    """
    url = "https://query.openkim.org/api"
    for param, val in params.items():
        params[param] = json.dumps(val)

    if endpoint is not None:
        url = ("/").join((url, endpoint))

    return requests.post(url, data=params).json()
