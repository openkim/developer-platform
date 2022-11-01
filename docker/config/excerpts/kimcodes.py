"""
This module is intended to handle anything related to KIM IDs, uuids, or jobids.

Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import re

from . import config as cf

RE_KIMID = r"^(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?$"
RE_EXTENDEDKIMID = (
    r"^(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))$"
)
RE_JOBID = (
    r"^([A-Z]{2}_[0-9]{12}_[0-9]{3})-and-([A-Z]{2}_[0-9]{12}_[0-9]{3})-([0-9]{5,})$"
)
RE_UUID = r"^([A-Z]{2}_[0-9]{12}_[0-9]{3})-and-([A-Z]{2}_[0-9]{12}_[0-9]{3})-([0-9]{5,})-([tve]r)$"
RE_TESTRESULT = r"^([A-Z]{2}_[0-9]{12}_[0-9]{3})-and-([A-Z]{2}_[0-9]{12}_[0-9]{3})-([0-9]{5,})-(tr)$"
RE_VERIFICATIONRESULT = r"^([A-Z]{2}_[0-9]{12}_[0-9]{3})-and-([A-Z]{2}_[0-9]{12}_[0-9]{3})-([0-9]{5,})-(vr)$"
RE_ERROR = r"^([A-Z]{2}_[0-9]{12}_[0-9]{3})-and-([A-Z]{2}_[0-9]{12}_[0-9]{3})-([0-9]{5,})-(er)$"


def parse_kim_code(kim_code):
    """Parse a kim code into it's pieces,
    returns a tuple (name,leader,num,version)"""
    rekimid = re.match(RE_KIMID, kim_code)
    rejobid = re.match(RE_JOBID, kim_code)
    reuuid = re.match(RE_UUID, kim_code)

    if rekimid:
        return rekimid.groups()
    elif rejobid:
        return rejobid.groups()
    elif reuuid:
        return reuuid.groups()
    else:
        raise cf.InvalidKIMCode(
            "{} is not a valid KIM ID, job id, or uuid".format(kim_code)
        )


def get_leader(kimid):
    """NOTE: This function is only to be used with KIM IDs, not UUIDs."""
    rekimid = re.match(RE_KIMID, kimid)

    if rekimid:
        return rekimid.groups()[1]
    else:
        raise cf.InvalidKIMCode("{} is not a valid KIM ID".format(kimid))


def format_kim_code(name, leader, num, version):
    """Format a KIM id into its proper form, assuming the form

    {name}__{leader}_{number}_{version}
    """
    # Cast num and version to strings in case they are passed in as ints
    name = str(name)
    version = str(version)

    assert leader, "A leader is required to format a kimcode"
    assert num, "A number is required to format a kimcode"
    assert version, "A version is required to format a kimcode"

    if name:
        if version:
            version = stringify_version(version)
            return "{}__{}_{}_{}".format(name, leader, num, version)
        else:
            return "{}__{}_{}".format(name, leader, num)
    else:
        version = stringify_version(version)
        return "{}_{}_{}".format(leader, num, version)


def strip_version(kimcode):
    name, leader, num, _ = parse_kim_code(kimcode)
    return "{}__{}_{}".format(name, leader, num)


def strip_name(kimcode):
    _, leader, num, version = parse_kim_code(kimcode)
    return "{}_{}_{}".format(leader, num, version)


def stringify_version(version):
    return str(version).zfill(3)


def iskimid(kimcode):
    return re.match(RE_KIMID, kimcode) is not None


def isextendedkimid(kimcode):
    return re.match(RE_EXTENDEDKIMID, kimcode) is not None


def isuuid(kimcode):
    return re.match(RE_UUID, kimcode) is not None


def isjobid(kimcode):
    return re.match(RE_JOBID, kimcode) is not None


def istestresult(uuid):
    return re.match(RE_TESTRESULT, uuid) is not None


def isverificationresult(uuid):
    return re.match(RE_VERIFICATIONRESULT, uuid) is not None


def iserror(uuid):
    return re.match(RE_ERROR, uuid) is not None
