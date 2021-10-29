#!/usr/bin/env python3
__python_requires__ = "~= 3.7"
__requires__ = ["click >= 7.0", "packaging"]
from datetime import date
import json
import re
from typing import Any, Dict
import click
from packaging.version import Version

DATA_V0 = "pyversion-info-data.json"
DATA_V1 = "pyversion-info-data.v1.json"


def version2_arg(v):
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", v):
        raise ValueError(v)
    return v


def version3_arg(v):
    if not re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", v):
        raise ValueError(v)
    return v


def date_arg(s):
    date.fromisoformat(s)  # Raises ValueError on failure
    return s


@click.group()
def main():
    """Update the pyversion info databases"""
    pass


@main.group()
def cpython():
    """Update the databases of CPython releases"""
    pass


@cpython.command("release")
@click.argument("version", type=version3_arg)
@click.argument("reldate", type=date_arg)
def cpython_release(version, reldate):
    """Add a new X.Y.Z release to the databases"""
    with open(DATA_V0) as fp:
        data = json.load(fp)
    set_version_datum(data, ["version_release_dates"], version, reldate)
    with open(DATA_V0, "w") as fp:
        print(json.dumps(data, indent=4), file=fp)

    with open(DATA_V1) as fp:
        data = json.load(fp)
    set_version_datum(data, ["cpython", "release_dates"], version, reldate)
    with open(DATA_V1, "w") as fp:
        print(json.dumps(data, indent=4), file=fp)


@cpython.command()
@click.argument("version", type=version2_arg)
@click.argument("eoldate", type=date_arg)
def eol(version, eoldate):
    """Add a new X.Y EOL date to the databases"""
    with open(DATA_V0) as fp:
        data = json.load(fp)
    set_version_datum(data, ["series_eol_dates"], version, eoldate)
    with open(DATA_V0, "w") as fp:
        print(json.dumps(data, indent=4), file=fp)

    with open(DATA_V1) as fp:
        data = json.load(fp)
    set_version_datum(data, ["cpython", "eol_dates"], version, eoldate)
    with open(DATA_V1, "w") as fp:
        print(json.dumps(data, indent=4), file=fp)


@main.group()
def pypy():
    """Update the database of PyPy releases"""
    pass


@pypy.command("release")
@click.argument("version", type=version3_arg)
@click.argument("reldate", type=date_arg)
@click.argument("cpythons", type=version3_arg, nargs=-1, required=True)
def pypy_release(version, reldate, cpythons):
    """Add a new X.Y.Z release to the database"""
    with open(DATA_V1) as fp:
        data = json.load(fp)
    set_version_datum(data, ["pypy", "release_dates"], version, reldate)
    set_version_datum(
        data, ["pypy", "cpython_versions"], version, sorted(cpythons, key=Version)
    )
    with open(DATA_V1, "w") as fp:
        print(json.dumps(data, indent=4), file=fp)


def set_version_datum(data, path, version, datum):
    d = data
    for p in path[:-1]:
        d = d[p]
    d[path[-1]] = sort_version_dict({**d[path[-1]], version: datum})


def sort_version_dict(vdict: Dict[str, Any]) -> Dict[str, Any]:
    return {v: vdict[v] for v in sorted(vdict, key=Version)}


if __name__ == "__main__":
    main()
