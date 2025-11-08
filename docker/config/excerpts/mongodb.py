"""
Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""

import os
import re
import datetime

from montydb import MontyClient, set_storage

from . import config as cf
from . import util
from . import kimobjects
from .kimcodes import parse_kim_code, isextendedkimid, isuuid

PIPELINE_LOCAL_DB_PATH = cf.LOCAL_DATABASE_PATH

set_storage(repository=PIPELINE_LOCAL_DB_PATH, use_bson=True, cache_modified="0")
client = MontyClient(PIPELINE_LOCAL_DB_PATH)
db = client.db

PATH_RESULT = cf.LOCAL_REPOSITORY_PATH
PATH_APPROVED = cf.LOCAL_REPOSITORY_PATH

indent = " " * 2


def config_edn(flname):
    with open(flname) as f:
        doc = util.loadedn(f)
        doc.setdefault(
            "created_on", str(datetime.datetime.fromtimestamp(os.path.getctime(flname)))
        )
        return doc


def drop_tables(ask=True):
    if ask:
        check = eval(input("Are you sure? [y/n] "))
    else:
        check = "y"

    if check == "y":
        db["data"].drop()


BADKEYS = {"kimspec", "profiling", "inserted_on", "latest"}


def rmbadkeys(dd):
    return {k: v for k, v in list(dd.items()) if k not in BADKEYS}


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
        ll = [flatten(item) for item in o]
        return ll
    else:
        return o


def kimcode_to_dict(kimcode):
    """
    Given the kimcode of an object or result/error, create a dict to insert into the
    'data' and 'obj' mongo databases. This includes reading the associated kimspec.edn
    from the appropriate folder in the local repository.  Furthermore, if the kimcode
    given corresponds to a Test, the dependencies.edn file is read and a key is created
    in the dictionary that is returned.
    """
    if isextendedkimid(kimcode):
        name, leader, num, version = parse_kim_code(kimcode)
    else:
        raise cf.InvalidKIMCode(
            "Received {} for insertion into mongo db. Only full extended KIM "
            "IDs (with version) are supported".format(kimcode)
        )

    leader = leader.lower()

    extended_id = None
    short_id = None
    m = re.search(r"(.+)__([A-Z]{2}_\d{12}_\d{3})$", kimcode)
    if m:
        extended_id = kimcode
        short_id = m.group(2)
    else:
        short_id = kimcode

    foo = {}
    if extended_id:
        foo["extended-id"] = extended_id
    foo["short-id"] = short_id
    if extended_id:
        foo["kimid-prefix"] = name
    foo["kimid-typecode"] = leader.lower()
    foo["kimid-number"] = num
    foo["kimid-version"] = version
    foo["kimid-version-as-integer"] = int(version)
    foo["name"] = name
    foo["type"] = leader.lower()
    foo["kimnum"] = num
    foo["version"] = int(version)
    foo["shortcode"] = "_".join((leader.upper(), num))
    foo["kimcode"] = kimcode
    foo["path"] = os.path.join(leader.lower(), kimcode)
    foo["approved"] = True
    foo["_id"] = kimcode
    foo["inserted_on"] = str(datetime.datetime.utcnow())
    foo["latest"] = True

    if foo["type"] in ("te", "mo", "sm", "td", "md", "vc"):
        foo["makeable"] = True
    if foo["type"] in ("te", "vc"):
        foo["runner"] = True
    if foo["type"] in ("sm", "mo"):
        foo["subject"] = True
    if foo["type"] in ("md", "td"):
        foo["driver"] = True
    else:
        foo["driver"] = False

    specpath = os.path.join(
        PATH_APPROVED, cf.item_subdir_names[leader], kimcode, cf.CONFIG_FILE
    )
    spec = config_edn(specpath)

    if foo["type"] == "te":
        # Fetch Test Driver, if any, from kimspec dict we loaded
        testresult = spec.get("test-driver", None)
        if testresult:
            foo["driver"] = rmbadkeys(kimcode_to_dict(testresult))

        # Fetch list of Tests in dependencies.edn, if it exists
        kobj = kimobjects.kim_obj(kimcode)
        foo["dependencies"] = kobj.runtime_dependencies()

    if foo["type"] == "mo":
        modeldriver = spec.get("model-driver", None)
        if modeldriver:
            foo["driver"] = rmbadkeys(kimcode_to_dict(modeldriver))

    foo.update(spec)
    return foo


def uuid_to_dict(leader, uuid):
    foo = {
        "uuid": uuid,
        "path": os.path.join(leader.lower(), uuid),
        "type": leader,
        "_id": uuid,
        "inserted_on": str(datetime.datetime.utcnow()),
        "latest": True,
    }

    specpath = os.path.join(
        PATH_RESULT, cf.item_subdir_names[leader], uuid, cf.CONFIG_FILE
    )
    spec = config_edn(specpath)

    pipespec = {}
    try:
        pipespecpath = os.path.join(
            PATH_RESULT, cf.item_subdir_names[leader], uuid, cf.PIPELINESPEC_FILE
        )
        pipespec = config_edn(pipespecpath)
    except:
        pass

    # Extend runner and subject
    runner = None
    subject = None
    if leader == "tr":
        # If this is a Test Result, get the test and model documents (cleaned up)
        runner = rmbadkeys(kimcode_to_dict(spec["test"]))

        if spec.get("model"):
            subject = rmbadkeys(kimcode_to_dict(spec["model"]))
        elif spec.get("simulator-model"):
            subject = rmbadkeys(kimcode_to_dict(spec["simulator-model"]))

    elif leader == "vr":
        # If this is a Verification Result, get Verification Check and the Model it
        # was paired with
        runner_code = spec.get("verification-check")
        if runner_code is None:
            print("No valid key for runner found in kimspec.edn of %r" % uuid)
            raise cf.PipelineDataMissing(
                "No valid key for runner found in kimspec.edn of %r" % uuid
            )
        runner = rmbadkeys(kimcode_to_dict(runner_code))

        if spec.get("model"):
            subject_code = spec["model"]
        elif spec.get("simulator-model"):
            subject_code = spec["simulator-model"]

        if subject_code is None:
            print("No valid key for subject found in kimspec.edn of %r" % uuid)
            raise cf.PipelineDataMissing(
                "No valid key for subject found in kimspec.edn of %r" % uuid
            )
        subject = rmbadkeys(kimcode_to_dict(subject_code))

    elif leader == "er":
        # If this is an error, it could be either the result of a Test-Model pair or
        # a Verification Check-Model pair.

        # First, check if the runner is a VC, then try TE
        runner_code = spec.get("verification-check", None)
        if runner_code is None:
            runner_code = spec.get("test", None)
            if runner_code is None:
                print("No valid key for runner found in kimspec.edn of %r" % uuid)
                raise cf.PipelineDataMissing(
                    "No valid key for runner found in kimspec.edn of %r" % uuid
                )
        runner = rmbadkeys(kimcode_to_dict(runner_code))

        # First, check that the subject is a MO
        if spec.get("model"):
            subject_code = spec["model"]
        elif spec.get("simulator-model"):
            subject_code = spec["simulator-model"]

        if subject_code is None:
            print("No valid key for subject found in kimspec.edn of %r" % uuid)
            raise cf.PipelineDataMissing(
                "No valid key for subject found in kimspec.edn of %r" % uuid
            )
        subject = rmbadkeys(kimcode_to_dict(subject_code))

    if runner:
        foo["runner"] = runner
    if subject:
        foo["subject"] = subject

    foo.update(spec)
    foo.update(pipespec)
    return foo


def doc_to_dict(doc, leader, uuid):
    foo = doc
    # copy info about result obj
    result_obj_doc = uuid_to_dict(leader, uuid)
    meta = rmbadkeys(result_obj_doc)

    if leader == "tr":
        # If we are a TR get the test and model documents (cleaned up)
        runner = rmbadkeys(kimcode_to_dict(result_obj_doc["test"]))
        if result_obj_doc.get("model"):
            subject = rmbadkeys(kimcode_to_dict(result_obj_doc["model"]))
        elif result_obj_doc.get("simulator-model"):
            subject = rmbadkeys(kimcode_to_dict(result_obj_doc["simulator-model"]))

    elif leader == "vr":
        # IF we are a VR, get the Verification Check and the Model it
        # ran with
        runner_code = result_obj_doc.get("verification-check", None)
        if runner_code:
            runner = rmbadkeys(kimcode_to_dict(runner_code))

        if result_obj_doc.get("model", None):
            subject = rmbadkeys(kimcode_to_dict(result_obj_doc["model"]))
        elif result_obj_doc.get("simulator-model", None):
            subject = rmbadkeys(kimcode_to_dict(result_obj_doc["simulator-model"]))

    try:
        meta["runner"] = runner
    except:
        pass
    try:
        meta["subject"] = subject
    except:
        pass
    foo["meta"] = meta
    foo["created_on"] = result_obj_doc["created_on"]
    foo["inserted_on"] = result_obj_doc["inserted_on"]
    foo["latest"] = True
    return foo


def rebuild_latest_tags():
    """
    Build the latest: True/False tags for all test results in the database
    by finding the latest versions of all results
    """
    print(
        "Updating 'latest' attribute for all Test Results, Verification Results, and Errors"
    )
    objs = db.data.find(
        {"meta.type": {"$in": ["tr", "vr", "er"]}},
        {"meta.runner.kimid-number": 1, "meta.subject.kimid-number": 1},
    )
    objs = [
        (o.get("meta.runner.kimid-number"), o.get("meta.subject.kimid-number"))
        for o in objs
    ]

    # Only retain unique (runner_num, subject_num) combinations
    objs = list(set([tuple(sorted(t)) for t in objs]))
    for o in objs:
        set_latest_version_result_or_error(o[0], o[1])


def set_latest_version_result_or_error(runner_num, subject_num):
    """
    Sets the Test Result, Verification Result, or Error corresponding to the
    latest versions of a given subject and runner to have 'latest'=True.  Whether
    the outcomes of any previous pairings of the relevant lineages have been
    results or errors is ignored, and all of them will be marked with 'latest'=False.
    In the event that multiple results/errors exist for the pair formed by
    the highest versions of the runner and subject, the result or error with the
    most recent 'created_on' timestamp is set to 'latest'=True and all others are set
    to 'latest'=False.
    """
    # First, try to pull all existing results for this pair from mongo 'data'
    result = list(
        db.data.find(
            {
                "meta.runner.kimid-number": runner_num,
                "meta.subject.kimid-number": subject_num,
            }
        )
    )

    # If we have no results for this pair (which could occur if this function is being
    # called for a deletion of the last remaining result or error for the pair), exit gracefully
    if len(result) == 0:
        print(
            "No Test Result, Verification Result, or Error found in mongo 'data' database for "
            "pair (%r, %r)...skipping `latest` update." % (runner_num, subject_num)
        )
        return

    result = result[0]["meta"]
    if "runner" not in result or "subject" not in result:
        print(
            "Test result, Verification Result, or Error found in mongo 'data' database for "
            "pair (%r, %r) ill-formed, missing runner and/or subject key."
            % (runner_num, subject_num)
        )
        return

    dbname = "data"

    # Set up prefixes for where to query
    prefix = "meta."

    query = {
        prefix + "runner.kimid-number": runner_num,
        prefix + "subject.kimid-number": subject_num,
    }

    fields = (
        prefix + "uuid",
        prefix + "runner.kimid-version",
        prefix + "subject.kimid-version",
        "created_on",
        "latest",
    )

    # Sort descendingly on each field.  First the result will be sorted on runner version,
    # then on subject version, then on 'created_on' timestamp.
    sort = [(i, -1) for i in fields[:3]]

    # Return all fields
    fields = {i: 1 for i in fields}

    results_and_errors = list(db[dbname].find(query, fields, sort=sort))

    # Get all the result or error ids that are relevant for our case, they
    # are sorted by latest as given by the previous query
    uuids = [
        res["meta"]["uuid"]
        for res in results_and_errors
        if "meta" in res and "uuid" in res["meta"]
    ]

    # Set all to have latest=False
    db[dbname].update_many(
        filter={prefix + "uuid": {"$in": uuids}}, update={"$set": {"latest": False}}
    )

    # Now set the most recent result or error to have latest=True
    db[dbname].update_many(
        filter={prefix + "uuid": uuids[0]},
        update={"$set": {"latest": True}},
    )


# =============================================================================
# Higher functions for inserting data
# =============================================================================
def insert_one_result(leader, uuid, full_result_path):
    print(indent + "Inserting result or error {} into local database".format(uuid))
    stuff = None
    info = uuid_to_dict(leader, uuid)

    if leader in ["tr", "vr"]:
        try:
            with open(os.path.join(full_result_path, cf.RESULT_FILE)) as f:
                edn_docs = util.loadedn(f)
                edn_docs = edn_docs if isinstance(edn_docs, list) else [edn_docs]
                for doc in edn_docs:
                    stuff = doc_to_dict(doc, leader, uuid)
                    db.data.insert_one(stuff)

            # Update 'latest' flag for this lineage-lineage set
            if leader == "tr":
                runner = info["test"]
            elif leader == "vr":
                runner = info["verification-check"]

            if "model" in info:
                subject = info["model"]
            elif "simulator-model" in info:
                subject = info["simulator-model"]

            _, _, runner_num, _ = parse_kim_code(runner)
            _, _, subject_num, _ = parse_kim_code(subject)
            set_latest_version_result_or_error(runner_num, subject_num)

        except:
            print("Could not read {} in {}/{}".format(cf.RESULT_FILE, leader, uuid))

    elif leader == "er":
        try:
            with open(
                os.path.join(PATH_RESULT, leader, uuid, "pipeline.exception")
            ) as f:
                doc = {"exception": f.read()}
            stuff = doc_to_dict(doc, leader, uuid)
            db.data.insert(stuff)

            # Update 'latest' flag for this lineage-lineage set
            if "test" in info:
                runner = info["test"]
            elif "verification-check" in info:
                runner = info["verification-check"]

            if "model" in info:
                subject = info["model"]
            elif "simulator-model" in info:
                subject = info["simulator-model"]

            _, _, runner_num, _ = parse_kim_code(runner)
            _, _, subject_num, _ = parse_kim_code(subject)
            set_latest_version_result_or_error(runner_num, subject_num)

        except:
            print("Could not insert exception for %s/%s", leader, uuid)


def insert_results():
    print("Filling with test results")
    leaders = ("tr", "vr", "er")
    for leader in leaders:
        for folder in sorted(os.listdir(os.path.join(PATH_RESULT, leader))):
            insert_one_result(leader, folder, [])


def delete_object(kimcode):
    db.data.remove({"meta.test-result-id": kimcode})
    db.data.remove({"meta.verification-result-id": kimcode})
    db.data.remove({"meta.error-result-id": kimcode})

    db.data.remove({"meta.runner.kimcode": kimcode})
    db.data.remove({"meta.subject.kimcode": kimcode})

    # Also delete immediate children and Test Results or Errors which
    # list this item as a driver
    # TODO: Still need full recursive propagation down here
    db.data.remove({"meta.runner.test-driver": kimcode})
    db.data.remove({"meta.subject.model-driver": kimcode})

    if isuuid(kimcode):
        runner, subject, _, _ = parse_kim_code(kimcode)
        _, _, runner_num, _ = parse_kim_code(runner)
        _, _, subject_num, _ = parse_kim_code(subject)
        set_latest_version_result_or_error(runner_num, subject_num)


def now():
    return str(datetime.datetime.now())
