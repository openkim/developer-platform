"""
Query OpenKIM for the kimnums of all reference data items
"""

import json
from send_openkim_query import send_openkim_query
KIMNUMS_FILENAME = "taken_rd_kimnums.json"

def query_for_taken_rd_kimnums():
    # get already-taken kimnums from OpenKIM
    query_params = {
        "database": "obj",
        "query": {"type":"rd"},
        "fields": {"kimnum": 1},
        "limit": 0,
        }
    try:
        all_rd_kimnum_dict = send_openkim_query(query_params, None)
    except:
        raise RuntimeError("KIM query failed")
    taken_kimnums = set()
    for entry in all_rd_kimnum_dict:
        taken_kimnums.add(entry["kimnum"]) 
    return taken_kimnums

if __name__ == "__main__":
    taken_kimnums = query_for_taken_rd_kimnums()
    with open(KIMNUMS_FILENAME,"w") as f:
        json.dump(list(taken_kimnums),f)