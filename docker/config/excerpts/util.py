"""
Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import os
import edn_format
import json
import subprocess
from functools import partial

from . import config as cf
from . import kimquery
from . import kimcodes
from .query_local import helper_functions

ImmutableList = edn_format.immutable_list.ImmutableList
ImmutableDict = edn_format.immutable_dict.ImmutableDict

jedns = partial(json.dumps, separators=(" ", " "), indent=4)


def replace_nones(o):
    if isinstance(o, list):
        return [replace_nones(i) for i in o]
    elif isinstance(o, dict):
        return {k: replace_nones(v) for k, v in list(o.items())}
    else:
        return o if o is not None else ""


def loadedn(f):
    """Load a file, filename, or string containing valid EDN into a dict.
    For whatever, reason, the 'edn_format' module always returns (nested)
    structures of its own internally defined types, ImmutableList and
    ImmutableDict.  Since we generally need to take the content we load
    from an EDN file and do something like json.dumps with it, this
    presents a problem.  Therefore, we recurse through them, converting all
    ImmutableList instances to regular python lists and all ImmutableDict
    instances to regular python dicts.

    NOTE: This function assumes that the content being loaded is always
    contained (at least at the uppermost level) in a dict or list, i.e. {}
    or [] brackets.  If not, we cowardly raise an exception.
    """

    def convert_immutablelist_to_list(l):
        """Go through all of the elements of this edn_format.ImmutableList
        object and convert them to either list or dict as appropriate"""
        if isinstance(l, ImmutableList):
            l = list(l)
            for ind, entry in enumerate(l):
                if isinstance(entry, ImmutableList):
                    l[ind] = convert_immutablelist_to_list(entry)
                elif isinstance(entry, ImmutableDict):
                    l[ind] = convert_immutabledict_to_dict(entry)
        return l

    def convert_immutabledict_to_dict(d):
        """Go through all of they key-value pairs  of this edn_format
        ImmutableDict object and convert the values to either list or dict as
        appropriate"""
        if isinstance(d, ImmutableDict):
            d = dict(d)
            for key, val in d.items():
                if isinstance(val, ImmutableList):
                    d[key] = convert_immutablelist_to_list(val)
                elif isinstance(val, ImmutableDict):
                    d[key] = convert_immutabledict_to_dict(val)
        return d

    if isinstance(f, str):
        try:
            # See if this is a file name
            with open(f, encoding="utf-8") as fo:
                c = fo.read()
                content = edn_format.loads(c, write_ply_tables=False)
        except IOError:
            # Assume it's a valid EDN-formatted string
            content = edn_format.loads(f, write_ply_tables=False)
    else:
        c = f.read()
        content = edn_format.loads(c, write_ply_tables=False)

    if isinstance(content, ImmutableList):
        content = convert_immutablelist_to_list(content)
    elif isinstance(content, ImmutableDict):
        content = convert_immutabledict_to_dict(content)
    else:
        raise cf.PipelineInvalidEDN(
            "Loaded EDN file or object {}, but it is "
            "not a list or dict.  Only lists or dicts are allowed.".format(f)
        )

    return content


def dumpedn(o, f, allow_nils=True):
    if not allow_nils:
        o = replace_nones(o)
    o = jedns(o)

    if isinstance(f, str):
        with open(f, "w", encoding="utf-8") as fi:
            fi.write(o)
            fi.write("\n")
    else:
        f.write(o)
        f.write("\n")


def mkdir_ext(p):
    if not os.path.exists(p):
        subprocess.check_call(["mkdir", "-p", p])


def flatten(o):
    if isinstance(o, dict):
        out = {}
        for key, value in list(o.items()):
            c = flatten(value)
            if isinstance(c, dict):
                out.update(
                    {key + "." + subkey: subval for subkey, subval in list(c.items())}
                )
            else:
                out.update({key: c})
        return out

    elif not isinstance(o, (str, bytes)) and hasattr(o, "__iter__"):
        return [flatten(item) for item in o]
    else:
        return o


def doproject(o, keys):
    if isinstance(o, dict):
        o = flatten(o)
        try:
            out = [o[key] for key in keys]
            if len(out) == 1:
                return out[0]
            return out
        except KeyError:
            return None

    if not isinstance(o, (str, bytes)) and hasattr(o, "__iter__"):
        ll = []
        for item in o:
            a = doproject(item, keys)
            if a is not None:
                ll.append(a)

        if len(ll) == 1:
            return ll[0]
        return ll
    else:
        raise o


def item_is_latest(kimcode):
    """
    Checks if a given item is the latest item in its lineage.  This automatically
    searches either the remote mongo database or the local database depending on the
    value of config.PIPELINE_LOCAL_DEV.

    Parameters
    ----------
    kimcode : str
        String uniquely identifying a Model, Simulator Model, Test, or Verification Check.
        This may be an extended KIM ID or a short ID (CC_DDDDDDDDDDDD_VVV).  In the
        latter case, the human-readable prefix is ignored.

    Returns
    -------
    Boolean indicating whether the kimcode given is the highest version of that
    item (in either the remote database or the local database in the container)
    """
    if cf.PIPELINE_LOCAL_DEV:
        return helper_functions.item_is_latest(kimcode)

    else:
        # Discard human-readable prefix, if any
        _, leader, num, ver = kimcodes.parse_kim_code(kimcode)
        short_id = ("_").join((leader, num, ver))
        leader = leader.lower()

        # Query remote database
        query = {
            "database": "obj",
            "query": {"short-id": short_id},
            "project": ["latest"],
            "limit": 1,
            "history": 1,
        }
        query_result = kimquery.query(query, decode=True)

        # Add handling for both array or scalar return in case we change that in the future (currently with projection
        # onto a single key, a scalar is returned)
        if isinstance(query_result, list):
            if query_result:
                latest_ver = query_result[0]
            else:
                # Couldn't find any results, so we must have the latest version of the item
                # as far as the local database is concerned
                return True
        else:
            latest_ver = query_result

        return ver == latest_ver
