"""
Provides a way to determine what items are in the user's local repository in
the container.  This is useful when the user has selected to use the local
database because only actual test results are inserted into it, i.e. it has a
'data' collection but not an 'obj' collection like the production mongo does.
It works by simply using glob patterns, similar

Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import os
import glob
import re

from . import config as cf

RE_KIMID = re.compile(
    r"^(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?$"
)


def match_on_pattern(item_types, pattern):
    """
    Search through the items of a given type in the local repository of the
    container and see if any match a given glob pattern
    """
    # If given a str corresponding to a single type, cast it to a list
    if isinstance(item_types, str):
        item_types = [item_types]

    matches = []
    for item_type in item_types:
        glob_pattern = os.path.join(
            cf.LOCAL_REPOSITORY_PATH, cf.item_subdir_names[item_type], pattern
        )
        # Strip off the front of the directory string from any matches
        match_results = [os.path.split(x)[-1] for x in glob.glob(glob_pattern)]
        matches += match_results
    return matches


def get_items_by_type(item_types):
    """
    Get all items, (both fresh and stale) of a given type in the local repository
    """
    # NOTE: We could switch this to use 'all_on_disk' KIMObject method to retrieve
    #       the actual objects and then grab the kimcodes out of them here

    # If given a str corresponding to a single type, cast it to a list
    if isinstance(item_types, str):
        item_types = [item_types]

    matches = []
    for item_type in item_types:
        matches += match_on_pattern(item_type, "*__" + item_type.upper() + "_*")
    return matches


def case_sensitive_local_search(pattern, path="."):
    RE = re.compile(pattern)
    return sorted(
        [
            os.path.split(name)[-1]
            for name in os.listdir(path)
            if RE_KIMID.match(name) and RE.search(name)
        ]
    )


def case_insensitive_local_search(pattern, path="."):
    RE = re.compile(pattern, re.IGNORECASE)
    return sorted(
        [
            os.path.split(name)[-1]
            for name in os.listdir(path)
            if RE_KIMID.match(name) and RE.search(name)
        ]
    )


def local_search(args):
    """
    Returns a unique set of kimcodes (just strings, not dicts)
    """
    if args["ignore_case"]:
        if args["type"]:
            hits = case_insensitive_local_search(
                args["search-term"],
                path=os.path.join(
                    cf.LOCAL_REPOSITORY_PATH, cf.item_subdir_names[args["type"]]
                ),
            )
        else:
            hits = []
            for subdir in ["te", "td", "mo", "md", "sm", "vc"]:
                hits = hits + case_insensitive_local_search(
                    args["search-term"],
                    path=os.path.join(
                        cf.LOCAL_REPOSITORY_PATH, cf.item_subdir_names[subdir]
                    ),
                )
    else:
        if args["type"]:
            hits = case_sensitive_local_search(
                args["search-term"],
                path=os.path.join(
                    cf.LOCAL_REPOSITORY_PATH, cf.item_subdir_names[args["type"]]
                ),
            )
        else:
            hits = []
            for subdir in ["te", "td", "mo", "md", "sm", "vc"]:
                hits = hits + case_sensitive_local_search(
                    args["search-term"],
                    path=os.path.join(
                        cf.LOCAL_REPOSITORY_PATH, cf.item_subdir_names[subdir]
                    ),
                )

    return sorted(set(hits))
