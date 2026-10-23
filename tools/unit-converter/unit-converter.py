#!/usr/bin/env python3
"""Convert between units: length, mass, temperature, data size, and time.

Usage:
    unit-converter.py 100 km mi
    unit-converter.py 32 F C
    unit-converter.py 5 GB MB
"""

import argparse
import sys

LENGTH = {"mm": 0.001, "cm": 0.01, "m": 1.0, "km": 1000.0,
          "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344}
MASS = {"mg": 1e-6, "g": 0.001, "kg": 1.0, "t": 1000.0,
        "oz": 0.028349523125, "lb": 0.45359237}
DATA = {"b": 1, "kb": 1000, "mb": 1000**2, "gb": 1000**3, "tb": 1000**4,
        "kib": 1024, "mib": 1024**2, "gib": 1024**3, "tib": 1024**4,
        "bit": 1 / 8, "kbit": 1000 / 8, "mbit": 1000**2 / 8, "gbit": 1000**3 / 8}
TIME = {"ms": 0.001, "s": 1.0, "min": 60.0, "h": 3600.0,
        "d": 86400.0, "w": 604800.0}
TEMP = {"c", "f", "k"}

GROUPS = {"length": LENGTH, "mass": MASS, "data": DATA, "time": TIME}


def convert_linear(value, from_u, to_u, table):
    return value * table[from_u] / table[to_u]


def convert_temp(value, from_u, to_u):
    if from_u == "c":
        c = value
    elif from_u == "f":
        c = (value - 32) * 5 / 9
    else:
        c = value - 273.15
    if to_u == "c":
        return c
    if to_u == "f":
        return c * 9 / 5 + 32
    return c + 273.15


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert between units (length, mass, temperature, data, time).",
        epilog="Examples:\n"
               "  unit-converter.py 100 km mi\n"
               "  unit-converter.py 32 F C\n"
               "  unit-converter.py 5 GiB MB\n"
               "  unit-converter.py 90 min h",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("value", type=float, help="numeric value to convert")
    parser.add_argument("from_unit", help="source unit, e.g. km")
    parser.add_argument("to_unit", help="target unit, e.g. mi")
    args = parser.parse_args(argv)

    fu, tu = args.from_unit.lower(), args.to_unit.lower()

    if fu in TEMP or tu in TEMP:
        if fu not in TEMP or tu not in TEMP:
            parser.error("cannot mix temperature with other unit types")
        result = convert_temp(args.value, fu, tu)
        print("%.6g %s = %.6g %s" % (args.value, args.from_unit, result, args.to_unit))
        return 0

    for name, table in GROUPS.items():
        if fu in table and tu in table:
            result = convert_linear(args.value, fu, tu, table)
            print("%.6g %s = %.6g %s" % (args.value, args.from_unit, result, args.to_unit))
            return 0
        if fu in table or tu in table:
            parser.error("units must be the same type (%s)" % name)

    all_units = sorted(set().union(*GROUPS.values()) | TEMP)
    parser.error("unknown unit(s). Known units: %s" % ", ".join(all_units))


if __name__ == "__main__":
    sys.exit(main())
