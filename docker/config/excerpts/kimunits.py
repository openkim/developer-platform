"""
Simple wrapper for executable for converting arbitrary units to SI units

Copyright (c) 2014-2022, Regents of the University of Minnesota. All rights
reserved.

This software may be distributed as-is, without modification.
"""

VERSION = 0.3

import re
import math
import subprocess
import warnings

warnings.simplefilter("ignore")


class UnitConversion(Exception):
    """Class for unit conversion errors"""


_units_output_expression = re.compile(
    r"(?P<value>(?:[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?))(?: (?P<unit>.+))?"
)


def linear_fit(x, y):
    """
    Perform a linear fit between x,y, returning the average error for each data
    point as well. This is written this way so as to not add a numpy dependency
    """
    n = len(x)
    xx = sum([x**2 for x in x]) - sum(x) ** 2 / n
    xy = sum(map(lambda x, y: x * y, x, y)) - sum(x) * sum(y) / n
    a, b = sum(y) / n - xy / xx * sum(x) / n, xy / xx
    yhat = [a + b * x for x in x]
    yerr = math.sqrt(sum(map(lambda y, yh: (y - yh) ** 2 / y**2, y, yhat)) / n)
    return a, b, yerr


def islinear(unit, to_unit=None):
    """
    Detect if the conversion from `unit` to `to_unit` is a linear map. Apparently
    the units utility is float precision, so if error is less than 1e-7 we know
    it is linear.
    """
    x = [100 ** (1e-2 * (i - 50)) for i in range(20)]
    y = convert_list(x, unit, to_unit=to_unit, dofit=False)[0]
    a, b, err = linear_fit(x, y)

    a = convert_list(0, unit, to_unit=to_unit, dofit=False)[0]
    b = convert_list(1, unit, to_unit=to_unit, dofit=False)[0] - a
    return a, b, err < 1e-7


def convert_units(from_value, from_unit, wanted_unit=None, suppress_unit=False):
    """Works with 'units' utility"""
    from_sign = from_value < 0
    from_value = str(abs(from_value))
    from_unit = str(from_unit)

    TEMPERATURE_FUNCTION_UNITS = ["degC", "tempC", "degF", "tempF"]

    if from_unit in TEMPERATURE_FUNCTION_UNITS:
        args = [
            "units",
            "-o",
            "%1.15e",
            "-qt1",
            "".join((from_unit, "(", from_value, ")")),
        ]

    else:
        args = ["units", "-o", "%1.15e", "-qt1", " ".join((from_value, from_unit))]

    if wanted_unit:
        args.append(wanted_unit)

    try:
        output = subprocess.check_output(args).decode("utf-8")
    except subprocess.CalledProcessError:
        tag = wanted_unit if wanted_unit else "SI"
        raise UnitConversion(
            "Error in unit conversion of {} {} to {}".format(from_value, from_unit, tag)
        )

    matches = _units_output_expression.match(output).groupdict(None)
    out = ((-1) ** from_sign * float(matches["value"]), matches["unit"] or wanted_unit)

    if suppress_unit:
        return out[0]
    return out


# Set default behavior
convert = convert_units


def convert_list(x, from_unit, to_unit=None, convert=convert, dofit=True):
    """Thread conversion over a list, or list of lists"""
    # Need a list for scoping reasons

    # Constant shortcut
    if from_unit in (1, 1.0, "1"):
        to_unit = "1"

    # get the SI unit if none provided
    if to_unit is None:
        _, to_unit = convert(1.0, from_unit)

    def convert_inner(x, fit=None):
        if isinstance(x, (list, tuple)):
            return type(x)(convert_inner(i, fit=fit) for i in x)
        else:
            if to_unit == "1":
                return float(x)
            else:
                if fit is not None:
                    return fit[0] + fit[1] * x
                return float(convert(x, from_unit, to_unit, suppress_unit=True))

    # setup the linear fit if we are requested to simplify
    fit = None
    if dofit and isinstance(x, (list, tuple)) and len(x) > 20:
        a, b, linear = islinear(from_unit, to_unit)
        fit = (a, b) if linear else None

    output = convert_inner(x, fit=fit)
    return output, to_unit


def add_si_units(doc, convert=convert):
    """Given a document, add all of the appropriate si-units fields"""
    if isinstance(doc, dict):
        # check for a source-unit to defined a value with units
        if "source-unit" in doc:
            # we've found a place to add
            assert "source-value" in doc, "Badly formed doc"
            o_value = doc.get("source-value", None)
            o_unit = doc.get("source-unit", None)

            if o_value is None:
                raise UnitConversion("No source-value provided")
            if o_unit is None:
                raise UnitConversion("No source-unit provided")

            # convert the units and insert
            value, unit = convert_list(o_value, o_unit, convert=convert)
            si_dict = {"si-unit": unit, "si-value": value}
            doc = doc.copy()
            doc.update(si_dict)
            return doc
        else:
            # recurse
            return type(doc)(
                (key, add_si_units(value)) for key, value in list(doc.items())
            )

    elif isinstance(doc, (list, tuple)):
        return type(doc)(add_si_units(x) for x in doc)

    return doc
