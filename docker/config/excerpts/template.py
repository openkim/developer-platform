"""
Holds the templating logic for the kim preprocessor

We utilize jinja2 templating to expose certain functions to the templating
functionality of the pipeline.  As of this version, the following functions
are available

    * query(query) - run a general API query to query.openkim.org for any information
        including test results or reference data.  See query.openkim.org for
        information on formatting these queries
    * MODELNAME - a global variable which represents the name of the current running Model.
    * TESTNAME - the name of the current running Test, similar to MODELNAME.
    * VCNAME - the name of the current running Verification Check, similar to TESTNAME.
    * SUBJECTNAME, RUNNERNAME - alternatives to MODELNAME and TESTNAME
    * path(kim_code) - gives the path of the corresponding kim_code;
        the executable if its a test or a test driver, and the folder otherwise
    * convert(value, srcunit, dstunit) - convert a floating point value from
        one unit to another
    * asedata - the dictionary of reference data contained within ASE

Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""

import os
import jinja2
import json
import edn_format
from functools import partial
from copy import deepcopy

from . import kimquery
from . import kimcodes
from . import kimobjects
from . import config as cf
from . import util
from .kimunits import convert


# -----------------------------------------
# New Template functions
# -----------------------------------------
def path(cand):
    if not kimcodes.isextendedkimid(cand):
        raise cf.PipelineTemplateError(
            "Template function path() received KIM "
            "ID {}. Only extended KIM IDs are valid input to this "
            "function.".format(cand)
        )

    obj = kimobjects.kim_obj(cand)
    try:
        p = obj.executable
    except AttributeError:
        p = obj.path

    return p


def stripversion(kim):
    kimtup = kimcodes.parse_kim_code(kim)
    newtup = (kimtup.name, kimtup.leader, kimtup.num, None)
    return kimcodes.format_kim_code(*newtup)


# custom json dump
jsondump = partial(json.dumps, indent=4)
edndump = partial(edn_format.dumps)

# -----------------------------------------
# Jinja Stuff
# -----------------------------------------
template_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader("/"),
    block_start_string="@[",
    block_end_string="]@",
    variable_start_string="@<",
    variable_end_string=">@",
    comment_start_string="@#",
    comment_end_string="#@",
    undefined=jinja2.StrictUndefined,
)

template_environment.filters.update(
    {
        "json": jsondump,
        "edn": edndump,
        "stripversion": stripversion,
    }
)


def intercept_query(query, subject_name, local, infofile):
    """
    Intercept any queries performed in pipeline.stdin.tpl. If these queries are to the 'data' database, we
    change the query as necessary in order to ensure that we get the 'meta.uuid' value back for all results
    returned by the query.  To accomplish this, we check if the 'fields' key contains 'meta.uuid'.  If it does
    not, we add it ourselves; after the query has returned a document, we then retrieve the 'meta.uuid' and
    remove the associated key-value pair from the dictionary.  In order for this to work, note that we also
    have to remove any 'project' specification from the query dictionary and apply it only after we've carried
    out this procedure.  In the event that 'fields' is blank, we do not need to add 'meta.uuid' (and, in fact,
    do not want to) since every key-value pair in the document will be returned.  However, we do still need to
    defer performing any projection until after we've already received the document from the query site.
    """
    # If no value for 'database' was given, set it to "data"
    database = query.get("database", "data")

    # If the user specified a query to a collection other than "data", simply send their query as-is
    if database != "data":
        return kimquery.query(query, local=local)
    else:
        # First, store the original query so that we can output it into pipeline.stdin.info as-is
        orig_query = deepcopy(query)

        # Check if any 'project' was given and, if so, strip it out and store it for later
        orig_project = query.pop("project", None)

        # If there was a non-empty 'fields' value given, store it and add 'meta.uuid' on to what's going to be
        # sent to the query site
        orig_fields = query.get("fields", None)
        if orig_fields:
            if "meta.uuid" in orig_fields:
                added_uuid_field = False
            else:
                added_uuid_field = True
                query["fields"].update({"meta.uuid": 1})

        add_history = not util.item_is_latest(subject_name)

        # If we're querying from pipeline.stdin.tpl for a stale Model, add history and sort accordingly
        if add_history:
            print(
                "WARNING: Querying for stale models will currently return ALL results for that model.\n"
                "If your pipeline.stdin.tpl query does not include a 'limit':1 option,\n"
                "you may get duplicate and/or 'double stale' (stale model and stale test) results.\n"
            )
            query["history"] = True
            orig_sort = query.get("sort", None)
            if orig_sort:
                if isinstance(orig_sort, str):
                    # If sort is a string, then it's ascending sort on that key alone. We need to cast it to a
                    # list so that we can add our own sorts onto it
                    query["sort"] = [
                        ["meta.runner.version", -1],
                        ["created_on", -1],
                        [orig_sort, -1],
                    ]
                elif isinstance(orig_sort, list):
                    # If the original sort was a list, then we know all of its elements are two-element lists
                    query["sort"].insert(0, ["created_on", -1])
                    query["sort"].insert(0, ["meta.runner.version", -1])
            else:
                query["sort"] = [["meta.runner.version", -1], ["created_on", -1]]

        # Perform our augmented query
        tmp_answer = kimquery.query(query, local=local, decode=True)

        # Record what the uuid of the corresponding result(s) was (were)
        if tmp_answer:
            if "meta.uuid" in tmp_answer[0]:
                flat = True
                # Write an entry into the infofile
                with open(infofile, "a", encoding="utf-8") as out:
                    out.write(
                        "Query {} matched documents for the following UUIDs: {}\n\n".format(
                            str(orig_query), [x["meta.uuid"] for x in tmp_answer]
                        )
                    )

            elif "meta" in tmp_answer[0]:
                flat = False
                # Write an entry into the infofile
                with open(infofile, "a", encoding="utf-8") as out:
                    out.write(
                        "Query {} matched documents for the following UUIDs: {}\n\n".format(
                            str(orig_query), [x["meta"]["uuid"] for x in tmp_answer]
                        )
                    )

            # If the user had specified 'fields', transform back to them (removing meta.uuid if we had added it)
            if orig_fields:
                if added_uuid_field:
                    if flat:
                        for doc in tmp_answer:
                            del doc["meta.uuid"]
                    else:
                        for doc in tmp_answer:
                            del doc["meta"]["uuid"]
                        # If there are no subkeys left in 'meta', delete it
                        if not doc["meta"]:
                            del doc["meta"]

            # Perform a project if the user had specified it
            if orig_project:
                tmp_answer = util.doproject(tmp_answer, orig_project)

            # Finally, pass the value, list, or dict back that user originally wanted
            return str(tmp_answer)

        else:
            with open(infofile, "a", encoding="utf-8") as out:
                out.write(
                    "Query {} did not match any documents\n\n".format(str(orig_query))
                )

            return tmp_answer


def intercept_get_test_result(test, model, prop, keys, units, local, infofile):
    """
    Intercept any calls to get_test_result performed in pipeline.stdin.tpl.  Check if 'meta.uuid' is contained
    in the list of keys specified as input to the function.  If it is not, we add it ourselves as the last
    element of the 'keys' list (and add a corresponding 'units' entry of null).  After the query has returned
    a list, we extract the uuid before passing along the list that the Test initially expected.  Of course, if
    the call to get_test_result returns an empty list, we simply note that no matching documents were found
    (just as we do in the case of raw queries in pipeline.stdin.tpl).
    """
    # Check if 'meta.uuid' is in the original set of keys. If so, get its index. (If it's in the list more
    # than once, although extremely unlikely, just get the index of the first instance of it)
    if "meta.uuid" in keys:
        uuid_index = keys.index("meta.uuid")
        answer = kimquery.get_test_result(
            test, model, prop, keys, units, local, decode=True
        )
        if answer:
            uuid = answer[uuid_index]
    else:
        # Add 'meta.uuid' to the end of keys and a corresponding null entry to the end of units
        keys.append("meta.uuid")
        units.append(None)
        answer = kimquery.get_test_result(
            test, model, prop, keys, units, local, decode=True
        )

        # Revert keys and units to their original values by stripping off the last element
        del keys[-1]
        del units[-1]

        if answer:
            # Get uuid and strip it off of the list we got back
            uuid = answer[-1]
            del answer[-1]

    tmpstr = "get_test_result({}, {}, {}, {}, {})".format(
        test, model, prop, keys, units
    )
    if answer:
        with open(infofile, "a", encoding="utf-8") as out:
            out.write(
                "Query {} matched documents for the following UUIDs: {}\n\n".format(
                    tmpstr, str(uuid)
                )
            )
    else:
        with open(infofile, "a", encoding="utf-8") as out:
            out.write("Query {} did not match any documents\n\n".format(tmpstr))

    return answer


# add handy functions to global name space
template_environment.globals.update(
    {
        "path": path,
        "convert": convert,
        "parse_kim_code": kimcodes.parse_kim_code,
        "format_kim_code": kimcodes.format_kim_code,
    }
)


def process(
    inppath,
    subject,
    runner,
    outfile=os.path.join(cf.OUTPUT_DIR, cf.TEMP_INPUT_FILE),
    infofile=os.path.join(cf.OUTPUT_DIR, cf.TEMP_INPUT_INFO_FILE),
):
    """Takes in a path (relative to runner directory) and writes a processed copy to TEMP_INPUT_FILE."""

    with runner.in_dir():
        if not os.path.exists(cf.OUTPUT_DIR):
            os.makedirs(cf.OUTPUT_DIR)

        template = template_environment.get_template(inppath)

        subject_name = subject.kim_code

        template.globals.update(
            {
                "query": partial(
                    intercept_query,
                    subject_name=subject_name,
                    local=cf.PIPELINE_LOCAL_DEV,
                    infofile=infofile,
                )
            }
        )
        template.globals.update(
            {
                "get_test_result": partial(
                    intercept_get_test_result,
                    local=cf.PIPELINE_LOCAL_DEV,
                    infofile=infofile,
                )
            }
        )

        extrainfo = {"RUNNERNAME": runner.kim_code, "SUBJECTNAME": subject_name}

        if runner.kim_code_leader.lower() == "te":
            extrainfo["MODELNAME"] = subject_name
            extrainfo["TESTNAME"] = runner.kim_code
        elif runner.kim_code_leader.lower() == "vc":
            extrainfo["MODELNAME"] = subject_name
            extrainfo["VCNAME"] = runner.kim_code

        output = template.render(**extrainfo)

        if not outfile:
            return output

        # Write the final processed stdin template to the output directory
        with open(outfile, "w", encoding="utf-8") as out:
            out.write(output)
