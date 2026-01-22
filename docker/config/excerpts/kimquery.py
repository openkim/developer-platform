"""
Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""

import urllib.request, urllib.error, urllib.parse
from . import config as cf
import json
import ssl

from .query_local import queryapi


def stringify_dict(query):
    output = {}
    for k, v in list(query.items()):
        output[k] = json.dumps(v)
    return output


def open_url(url, data, header, use_SSL=False, timeout=None):
    request = urllib.request.Request(url, data.encode("utf-8"), header)

    if use_SSL:
        response = urllib.request.urlopen(request, timeout=timeout)
    else:
        context = ssl._create_unverified_context()
        response = urllib.request.urlopen(request, context=context, timeout=timeout)

    answer = response.read()
    response.close()
    return answer


def query_mongo(query, local=False, decode=False):

    if local:
        from .mongodb import db
        from bson.json_util import dumps

        # Cast each val in query dict to str
        query = stringify_dict(query)
        answer = dumps(queryapi.api_v0(db, query))

    else:
        url = cf.PIPELINE_REMOTE_QUERY_ADDRESS
        use_SSL = True

        header = {"Content-type": "application/x-www-form-urlencoded"}

        data = urllib.parse.urlencode(
            dict((key, json.dumps(val)) for (key, val) in list(query.items()))
        )

        answer = open_url(url, data, header, use_SSL)

        if not answer:
            raise cf.PipelineQueryError("No response")
        elif isinstance(answer, bytes):
            answer = answer.decode("utf-8")

        # We got back JSON, let's check if we got errors back
        check = json.loads(answer)
        if isinstance(check, dict) and check.get("error"):
            raise cf.PipelineQueryError("{}".format(check["error"]))

    if decode:
        return json.loads(answer)

    return answer


def get_test_result(test, model, prop, keys, units, local=False, decode=False):

    url = cf.PIPELINE_REMOTE_QUERY_ADDRESS + "/get_test_result"
    use_SSL = True

    header = {"Content-type": "application/x-www-form-urlencoded"}

    d = {}
    d["test"] = test
    d["model"] = model
    d["prop"] = prop
    d["keys"] = json.dumps(keys)
    d["units"] = json.dumps(units)
    data = urllib.parse.urlencode(d)

    answer = open_url(url, data, header, use_SSL)

    if not answer:
        raise cf.PipelineQueryError("No response")

    # We got back JSON, let's check if we got errors back
    check = json.loads(answer)
    if isinstance(check, dict) and check.get("error"):
        raise cf.PipelineQueryError("Error received: {}".format(check["error"]))

    if decode:
        return json.loads(answer)
    return answer


query = query_mongo
