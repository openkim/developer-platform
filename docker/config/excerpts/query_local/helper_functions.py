"""
Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""
import re
from json.decoder import JSONDecodeError
import inspect

from bson.json_util import loads

from .. import kimquery
from ..kimcodes import parse_kim_code
from ..kimunits import convert_units, convert_list, UnitConversion

RE_KIMID = r"^(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?$"
RE_EXTENDED_ID = r"^[A-Za-z0-9_]+__[A-Z]{2}_[0-9]{12}_[0-9]{3}$"
RE_SHORT_ID = r"^[A-Z]{2}_[0-9]{12}_[0-9]{3}$"
RE_EXTENDED_ID_NO_VERSION = r"^[A-Za-z0-9_]+__[A-Z]{2}_[0-9]{12}"
RE_SHORTCODE = r"^[A-Z]{2}_[0-9]{12}$"
RE_PROPERTY_ID_GROUPED = (
    r"^tag:([^A-Z+]+@[^A-Z+]+),([0-9]{4}-[0-9]{2}-[0-9]{2}):property\/([a-z-]+)$"
)


#######################################################################################
# For handlers
#######################################################################################


def printable(v):
    return re.sub("<", "&lt;", re.sub(">", "&gt;", v))


class dotdict(dict):
    __getattr__ = dict.get


def load_json_dict(data, allow_decode_error=False):
    out = {}
    for k, v in list(data.items()):
        if not v:
            continue
        try:
            val = loads(v)
        except JSONDecodeError:
            if allow_decode_error:
                val = v
            else:
                raise ValueError("Could not load input '{}' as valid JSON".format(k))
        out[k] = val

    return out


#######################################################################################
# For query api functions
#######################################################################################


def strip_null(dic):
    out = {}
    for k, v in list(dic.items()):
        if v is not None:
            out[k] = v
    return out


def check_input_args_are_lists(inputs):
    for inp, val in inputs.items():
        if not isinstance(val, list):
            raise ValueError(
                "Input argument '{}' to function {}() must be a list".format(
                    inp, inspect.stack()[1].function
                )
            )


def check_types_in_input_arg(argname, argval, datatypes):
    """Go through a single input argument (which is always a list) and make sure all
    elements are of the specified data type. We refrain from using all() because we
    want a very verbose error message"""
    for ind, element in enumerate(argval):
        if not isinstance(element, datatypes):
            raise ValueError(
                "Each member of the '{}' input argument passed to function {}() must be "
                "of the following types:  {}.  Offending item value: {}, Type of "
                "offending item: {}, Zero-based index of offending item: {}".format(
                    argname,
                    inspect.stack()[1].function,
                    [d.__name__ for d in datatypes],
                    element,
                    type(element).__name__,
                    ind,
                )
            )


def check_for_invalid_null(units):
    """See if the user erroneously used a string while trying to specify that the value
    being returned has no units.  This wouldn't be caught by the JSON decoding done by
    the API handler"""
    for ind, element in enumerate(units):
        if element in ["None", "none", "Null", "null"]:
            raise ValueError(
                "In order to specify that no units should be returned, use the JSON "
                'keyword null (without quotes).  Offending item value: "{}", Zero-based '
                "index of offending item: {}".format(element, ind)
            )


def modify_query_for_item(query, item_type, item_id):
    """
    Given a query dictionary and a runner or subject ID, determine if the ID is:
      - A valid extended KIM ID
      - A valid short ID (has suffix)
      - An extended KIM ID with no version suffix
      - A short ID with no version suffix
    and modify the query dictionary accordingly.  This modification consists of
    selecting the appropriate key name as well as possibly turning history on.  Note
    that the human-readable prefix, if one is given, is discarded at this stage.  The
    return value of this function is a boolean indicating whether the ID had a version
    specified in it or not.
    """
    try:
        _, leader, num, ver = re.match(RE_KIMID, item_id).groups()
    except AttributeError:
        item_type_to_key = {
            "runner": "test",
            "subject": "model",
            "runner.driver": "method",
        }
        raise ValueError(
            "Invalid {} '{}' passed to function {}()".format(
                item_type_to_key[item_type], item_id, inspect.stack()[1].function
            )
        )

    if ver:
        shortid = ("_").join((leader, num, ver))
        query["query"][(".").join(("meta", item_type, "short-id"))] = shortid
        query["history"] = 1
    else:
        shortcode = ("_").join((leader, num))
        query["query"][(".").join(("meta", item_type, "shortcode"))] = shortcode

    return ver is not None


def modify_query_for_species(query, species):
    """If the species list passed in contains a single element, we need to grab the set of Test
    Results for which each and every member of species.source-value is equal to the element
    name passed in as 'species'.  If more than one element was passed in as 'species', make
    sure the species.source-value array in the Test Results we're querying on possesses each
    element in 'species' at least once, and contains no other elements.
    """
    # FIXME: Can this be optimized?
    query["query"]["species.source-value"] = {
        "$all": species,
        "$not": {"$elemMatch": {"$nin": species}},
    }


def convert_from_si(key, from_val, from_units, to_units):
    if type(from_val) is list:
        if to_units.upper() == "SI":
            converted_val = from_val  # The result we have is already in SI units
        else:
            try:
                converted_val = convert_list(
                    x=from_val, from_unit=from_units, to_unit=to_units, dofit=False
                )[0]
            except UnitConversion as e:
                raise RuntimeError(
                    "Unable to convert key '{}' to units of {}".format(
                        key, to_units, inspect.stack()[1].function
                    )
                ) from e

    else:
        if to_units.upper() == "SI":
            converted_val = from_val  # The result we have is already in SI units
        else:
            try:
                converted_val = convert_units(
                    from_value=from_val,
                    from_unit=from_units,
                    wanted_unit=to_units,
                    suppress_unit=True,
                )
            except UnitConversion as e:
                raise RuntimeError(
                    "Unable to convert key '{}' to units of {}".format(key, to_units)
                ) from e

    return converted_val


def extract_key_from_result(final_TestResult, key, to_units):
    if to_units is None:
        try:
            return final_TestResult[key]
        except:
            # If we were unable to find the key as-is in final_TestResult, one of the following
            # is true:
            # 1.) Is an invalid key that doesn't exist in the property definition
            # 2.) It has 'si-value' and 'si-units' attached to it, e.g. non-dimensional atomic
            # coordinates
            # 3.) It has 'si-value', 'si-units', 'source-value', and 'source-units' attached
            # to it
            #
            # If it has si-value attached to it, tell the user they need to give units for this
            # key
            if key + ".si-value" in final_TestResult:
                raise ValueError(
                    "Units were specified as None for key '{}' in function {}(), but "
                    "units must be associated with it according to the property "
                    "definition specified".format(key, inspect.stack()[1].function)
                )
            else:
                # If it does not have si-value attached to it, but does have source-unit
                # associated with it, add it to the final results list
                if key + ".source-value" in final_TestResult:
                    return final_TestResult[key + ".source-value"]
                else:
                    raise RuntimeError(
                        "UNKNOWN ERROR code 001 occurred from function {}()"
                        "".format(inspect.stack()[1].function)
                    )
    else:
        try:
            this_val = final_TestResult[key + ".si-value"]
        except:
            raise ValueError(
                "Units were specified for key '{}' in function {}(), but it has no "
                "associated units in the property definition specified".format(
                    key, inspect.stack()[1].function
                )
            )
        this_units = final_TestResult[key + ".si-unit"]
        converted_val = convert_from_si(
            key, this_val, from_units=this_units, to_units=to_units
        )
        return converted_val


def initialize_test_result_query():
    """Initialize dictionary that defines mongodb query. All Test Results are under the
    'data' database and have meta.type = 'tr'"""
    query = {}
    query["query"] = {}
    query["fields"] = {}
    query["fields"]["property-id"] = 1
    query["fields"]["meta.runner.version"] = 1
    query["fields"]["meta.runner.driver.version"] = 1
    query["fields"]["meta.subject.version"] = 1
    query["fields"]["meta.uuid"] = 1
    query["fields"]["meta.type"] = 1
    query["database"] = "data"
    query["flat"] = 1

    return query


def sort_on_property_date(results_from_query):
    return sorted(
        results_from_query,
        key=lambda k: re.search(RE_PROPERTY_ID_GROUPED, k["property-id"]).groups(1),
        reverse=True,
    )


def sort_on_Test_ver(results_from_query):
    return sorted(
        results_from_query, key=lambda k: k["meta.runner.version"], reverse=True
    )


def sort_on_TestDriver_ver(results_from_query):
    return sorted(
        results_from_query, key=lambda k: k["meta.runner.driver.version"], reverse=True
    )


def sort_on_Model_ver(results_from_query):
    return sorted(
        results_from_query, key=lambda k: k["meta.subject.version"], reverse=True
    )


def filter_on_item_versions_and_timestamp(results_from_query):
    """
    Given an array of dictionaries of results/errors, check to see which of them
    correspond to the highest TD, TE and MO or SM versions, as well as the highest
    timestamp for that combination of versions, and retain them.  Discard the rest of
    the results or errors.  Note this will work even if a specific TE-MO or TE-SM
    combination reports more than one property instance at a time.  Finally, remove all
    errors from the list of results (note this has to be done here in this function,
    AFTER we've already filtered on item versions; if you tried to use meta.type=tr as a
    query parameter, it may exclude an error that's produced by the highest versions of
    the relevant items if history is on)
    """
    # First, filter by Test Driver
    highest_TestDriver_ver = max(
        set([instance["meta.runner.driver.version"] for instance in results_from_query])
    )
    highest_Test_ver = max(
        set([instance["meta.runner.version"] for instance in results_from_query])
    )
    highest_subject_ver = max(
        set([instance["meta.subject.version"] for instance in results_from_query])
    )
    filtered_results = [
        instance
        for instance in results_from_query
        if (
            instance["meta.runner.driver.version"] == highest_TestDriver_ver
            and instance["meta.runner.version"] == highest_Test_ver
            and instance["meta.subject.version"] == highest_subject_ver
        )
    ]

    # Now filter by uuid and throw out errors
    filtered_results = sorted(
        filtered_results, key=lambda k: k["meta.uuid"], reverse=True
    )
    highest_uuid = filtered_results[0]["meta.uuid"]
    filtered_results = [
        instance
        for instance in results_from_query
        if (instance["meta.uuid"] == highest_uuid and instance["meta.type"] == "tr")
    ]

    return filtered_results


def filter_on_pressure(
    results_from_query,
    pressure,
    pressure_units,
    pressure_tol,
    stress_name="cauchy-stress",
):
    # Because we never get pressure back directly but rather only cauchy stress, we'll
    # have to do the checking on pressure manually since a map reduce would collapse all
    # results into one, which we don't want (there could be multiple results, each of
    # which corresponds to a different test).
    try:
        pressure_si, pressure_tol_si = convert_list(
            x=[pressure, pressure_tol],
            from_unit=pressure_units,
            to_unit="Pa",
            dofit=False,
        )[0]
    except UnitConversion as e:
        raise RuntimeError(
            "Invalid pressure_units '{}' " "given".format(pressure_units)
        ) from e

    final_TestResults = []

    for result in results_from_query:
        this_pressure_si = sum(result[stress_name + ".si-value"][:3]) / 3.0
        if abs(this_pressure_si - pressure_si) < pressure_tol_si:
            final_TestResults.append(result)

    if len(final_TestResults) > 1:
        raise RuntimeError(
            "Found multiple results that match the specified " "pressure"
        )

    return final_TestResults


def filter_on_temperature_and_pressure(
    results_from_query,
    temperature,
    temperature_units,
    temperature_tol,
    pressure,
    pressure_units,
    pressure_tol,
    stress_name="cauchy-stress",
):
    # Because we never get pressure back directly but rather only cauchy stress, we'll
    # have to do the checking on pressure manually since a map reduce would collapse all
    # results into one, which we don't want (there could be multiple results, each of
    # which corresponds to a different test).  To keep things simple, we also do the
    # checking on temperature_tol here manually
    try:
        temperature_si, temperature_tol_si = convert_list(
            x=[temperature, temperature_tol],
            from_unit=temperature_units,
            to_unit="K",
            dofit=False,
        )[0]
    except UnitConversion as e:
        raise RuntimeError(
            "Invalid temperature_units '{}' " "given".format(temperature_units)
        ) from e
    try:
        pressure_si, pressure_tol_si = convert_list(
            x=[pressure, pressure_tol],
            from_unit=pressure_units,
            to_unit="Pa",
            dofit=False,
        )[0]
    except UnitConversion as e:
        raise RuntimeError(
            "Invalid pressure_units '{}' " "given".format(pressure_units)
        ) from e

    final_TestResults = []

    for result in results_from_query:
        this_temp_si = result["temperature.si-value"]
        this_pressure_si = sum(result[stress_name + ".si-value"][:3]) / 3.0
        if (
            abs(this_temp_si - temperature_si) < temperature_tol_si
            and abs(this_pressure_si - pressure_si) < pressure_tol_si
        ):
            final_TestResults.append(result)

    if len(final_TestResults) > 1:
        raise RuntimeError(
            "Found multiple results that match the specified "
            "temperature and pressure"
        )

    return final_TestResults


def process_method(method_synonyms, method):
    """
    Given a list of allowed method names and a dict of synonyms, determine
    if the method provided is valid and, if so, return it with the human-readable
    prefix, if any, stripped off
    """
    method = method[0]
    # First, check if this is a synonym since that's the default
    try:
        return [method_synonyms[method]]
    except KeyError:
        try:
            # Try to parse it as a KIM ID
            name, leader, num, ver = re.match(RE_KIMID, method).groups()
        except AttributeError:
            raise ValueError(
                "Invalid value '{}' for argument 'method' passed to function {}()."
                "".format(method, inspect.stack()[1].function)
            )

        # Strip human-readable prefix
        if ver:
            return [("_").join((leader, num, ver))]
        else:
            return [("_").join((leader, num))]


def check_args_allowed_values(allowed_values, inputs):
    # Only check those keys that are listed in 'allowed_values'
    for key, vals in allowed_values.items():
        if inputs[key] not in vals:
            raise ValueError(
                "Invalid value '{}' for argument '{}' passed to function {}(). Allowed "
                "values are {}".format(
                    inputs[key], key, inspect.stack()[1].function, vals
                )
            )


#######################################################################################
# For query API
#######################################################################################


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
        # Object passed in is a list or pymongo cursor
        return [flatten(item) for item in o]

    else:
        return o


def doproject(o, keys):
    if isinstance(o, dict):
        try:
            out = [o[key] for key in keys]
            if len(out) == 1:
                return out[0]
            return out
        except KeyError:
            return None
    if hasattr(o, "__iter__"):
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


#######################################################################################
# For local db
#######################################################################################
def item_is_latest(kimcode):
    """
    Queries the local database, which contains only a 'data' collection, to see what
    the latest version of the lineage corresponding to the given kimcode is.

    Parameters
    ----------
    kimcode : str
        String uniquely identifying a Model, Simulator Model, Test, or Verification Check.
        This may be an extended KIM ID or a short ID (CC_DDDDDDDDDDDD_VVV).  In the
        latter case, the human-readable prefix is ignored.

    Returns
    -------
    Boolean indicating whether the kimcode given is the highest version of that
    item in the local database (True), or whether there are results in it that
    include an item in the lineage of the supplied kimcode that is of a higher
    version than the one given.
    """
    # Discard human-readable prefix, if any
    _, leader, num, ver = parse_kim_code(kimcode)
    shortcode = ("_").join((leader, num))
    leader = leader.lower()

    if leader in ["te", "vc"]:
        item_type = "runner"
    elif leader in ["mo", "sm"]:
        item_type = "subject"
    else:
        raise ValueError(
            "Invalid item {} is neither runner nor subject".format(kimcode)
        )

    # Don't need to turn on 'history' since we're interested in the latest
    query = {
        "database": "data",
        "query": {"meta." + item_type + ".shortcode": shortcode},
        "project": ["meta." + item_type + ".kimid-version"],
        "sort": [["meta." + item_type + ".kimid-version", -1]],
        "limit": 1,
    }

    query_result = kimquery.query(query, local=True, decode=True)

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
