#!/usr/bin/env python3
"""Perform various validations and sanity checks on the pyversion databases"""
__python_requires__ = "~= 3.7"
__requires__ = ["jsonschema[format] ~= 4.0"]
from bisect import bisect_left
from datetime import date, datetime
from typing import Iterable, List, Tuple
import json
from jsonschema import draft7_format_checker, validate

DATA_V0 = "pyversion-info-data.json"
SCHEMA_V0 = "pyversion-info-data.schema.json"
DATA_V1 = "pyversion-info-data.v1.json"
SCHEMA_V1 = "pyversion-info-data.v1.schema.json"


class VersionTrie:
    def __init__(self, version_list: Iterable[Tuple[int, int, int]]):
        self.version_trie = {}
        for x, y, z in version_list:
            self.version_trie.setdefault(x, {}).setdefault(y, []).append(z)

    def get_majors(self) -> List[int]:
        return list(self.version_trie.keys())

    def get_minors(self, major: int) -> List[int]:
        return list(self.version_trie.get(major, {}).keys())

    def get_micros(self, major: int, minor: int) -> List[int]:
        return self.version_trie.get(major, {}).get(minor, [])


def main():
    with open(DATA_V0) as fp:
        data_v0 = json.load(fp)
    with open(SCHEMA_V0) as fp:
        schema_v0 = json.load(fp)

    with open(DATA_V1) as fp:
        data = json.load(fp)
    with open(SCHEMA_V1) as fp:
        schema = json.load(fp)

    # Check that data files conform to schemata
    validate(data, schema, format_checker=draft7_format_checker)
    validate(data_v0, schema_v0, format_checker=draft7_format_checker)

    ### TODO: Show details when this fails (Use deepdiff?)
    assert downgrade(data) == data_v0, "CPython data differs between databases"

    validate_cpython(data["cpython"])
    validate_pypy(data["pypy"])


def validate_cpython(data):
    versions = [
        (parse_version(v), parse_date(d)) for v, d in data["release_dates"].items()
    ]
    versions.sort()

    vtrie = VersionTrie(v for v, _ in versions)

    # Check that each series has one or more micro versions
    for series in data["eol_dates"].keys():
        assert vtrie.get_micros(
            *parse_version(series)
        ), f"CPython: Series {series} present but does not have any versions"

    # Check that each micro version belongs to a series
    for v, _ in versions:
        s = unparse_version(v[:2])
        assert (
            s in data["eol_dates"]
        ), f"CPython: Version {unparse_version(v)} present but series {s} missing"

    # Check that all major versions form a set {0..n}
    assert_Zn(vtrie.get_majors(), "CPython: Major versions")

    # Check that, for each major version other than 0, the minor versions form
    # a set {0..n}
    for major in vtrie.get_majors():
        if major != 0:
            assert_Zn(vtrie.get_minors(major), f"CPython: Minor versions of v{major}")

    # Check that, for each minor version other than 0.Y, the micro versions
    # form a set {0..n}
    for major in vtrie.get_majors():
        if major != 0:
            for minor in vtrie.get_minors(major):
                assert_Zn(
                    vtrie.get_micros(major, minor),
                    f"CPython: Micro versions of v{major}.{minor}",
                )

    # Check that the major versions' first releases are in chronological order
    first_releases = []
    for major in vtrie.get_majors():
        first_v, first_date = versions[bisect_left(versions, ((major,), None))]
        assert first_v[0] == major
        first_releases.append(first_date)
    assert_chrono_order(first_releases, "CPython: Initial releases of major versions")

    # Check that, for each major version, the minor versions' first releases
    # are in chronological order
    for major in vtrie.get_majors():
        first_releases = []
        for m in vtrie.get_minors(major):
            first_v, first_date = versions[bisect_left(versions, ((major, m), None))]
            assert first_v[:2] == (major, m)
            first_releases.append(first_date)
        assert_chrono_order(
            first_releases, f"CPython: Initial releases of minor versions of v{major}"
        )

    # Check that each minor version's micro releases are in chronological order
    for major in vtrie.get_majors():
        for minor in vtrie.get_minors(major):
            releases = [
                data["release_dates"][unparse_version((major, minor, m))]
                for m in vtrie.get_micros(major, minor)
            ]
            assert_chrono_order(releases, f"CPython: Micro releases of {major}.{minor}")

    # Check that no micro versions are released after a series goes EOL
    # (Apparently, this can legitimately happen; see v2.7 and v3.0.)
    # for series, eol_date in data["eol_dates"].items():
    #     x, y = parse_version(series)
    #     if isinstance(eol_date, str):
    #         eol_date = parse_date(eol_date)
    #         for z in vtrie.get_micros(x, y):
    #             v = unparse_version((x, y, z))
    #             rel = parse_date(data["release_dates"][v])
    #             assert not isinstance(rel, date) or rel <= eol_date, \
    #                 f'Version {v} released after series EOL'


def validate_pypy(data):
    versions = [
        (parse_version(v), parse_date(d)) for v, d in data["release_dates"].items()
    ]
    versions.sort()

    vtrie = VersionTrie(v for v, _ in versions)

    # Check that every released PyPy version has CPython versions
    for v in data["release_dates"]:
        assert (
            v in data["cpython_versions"]
        ), f"PyPy: {v} present in 'release_dates' but not in 'cpython_versions'"
        assert data["cpython_versions"][
            v
        ], f"PyPy: list of CPython versions for {v} is empty"

    # Check that every version in cpython_versions has a release date
    for v in data["cpython_versions"]:
        assert (
            v in data["release_dates"]
        ), f"PyPy: {v} present in 'cpython_versions' but not in 'release_dates'"

    # Check that all major versions form a set {0..n} once 0 and 3 are added
    assert_Zn(vtrie.get_majors() + [0, 3], "PyPy: Major versions")

    # Check that, for each major version greater than 1, the minor versions
    # form a set {0..n}
    for major in vtrie.get_majors():
        if major > 1:
            minors = vtrie.get_minors(major)
            if major == 5:
                # v5.2 and v5.5 were all alpha releases and thus aren't in the
                # database
                minors = minors + [2, 5]
            assert_Zn(minors, f"PyPy: Minor versions of v{major}")

    # Check that, for each minor version, the micro versions form a set {0..n}
    for major in vtrie.get_majors():
        for minor in vtrie.get_minors(major):
            assert_Zn(
                vtrie.get_micros(major, minor),
                f"PyPy: Micro versions of v{major}.{minor}",
            )

    # Check that the major versions' first releases are in chronological order
    first_releases = []
    for major in vtrie.get_majors():
        first_v, first_date = versions[bisect_left(versions, ((major,), None))]
        assert first_v[0] == major
        first_releases.append(first_date)
    assert_chrono_order(first_releases, "PyPy: Initial releases of major versions")

    # Check that, for each major version, the minor versions' first releases
    # are in chronological order
    for major in vtrie.get_majors():
        first_releases = []
        for m in vtrie.get_minors(major):
            first_v, first_date = versions[bisect_left(versions, ((major, m), None))]
            assert first_v[:2] == (major, m)
            first_releases.append(first_date)
        assert_chrono_order(
            first_releases, f"PyPy: Initial releases of minor versions of v{major}"
        )

    # Check that each minor version's micro releases are in chronological order
    for major in vtrie.get_majors():
        for minor in vtrie.get_minors(major):
            releases = [
                data["release_dates"][unparse_version((major, minor, m))]
                for m in vtrie.get_micros(major, minor)
            ]
            assert_chrono_order(releases, f"PyPy: Micro releases of {major}.{minor}")


def parse_version(s):
    return tuple(map(int, s.split(".")))


def unparse_version(v):
    return ".".join(map(str, v))


def parse_date(s):
    if isinstance(s, str):
        return datetime.strptime(s, "%Y-%m-%d").date()
    else:
        return s


def assert_Zn(values, description):
    """
    >>> assert_Zn([0, 1, 2, 3, 4, 5], 'Test values')
    >>> assert_Zn([0, 1, 3, 4, 5, 6], 'Test values')
    Traceback (most recent call last):
        ...
    AssertionError: Test values not contiguous; missing 2
    """
    values = set(values)
    diff = set(range(len(values))) - values
    assert not diff, f"{description} not contiguous; missing {min(diff)}"


def assert_chrono_order(dates, description):
    """
    >>> assert_chrono_order([
    ...     date(2001, 4, 17),
    ...     date(2001, 7, 20),
    ...     date(2002, 1, 16),
    ...     date(2002, 4, 9),
    ... ], 'Test values')
    >>> assert_chrono_order([
    ...     None,
    ...     True,
    ...     date(2001, 4, 17),
    ...     date(2001, 7, 20),
    ...     True,
    ...     None,
    ...     date(2002, 1, 16),
    ...     date(2002, 4, 9),
    ... ], 'Test values')
    >>> assert_chrono_order([
    ...     date(2001, 4, 17),
    ...     date(2002, 1, 16),
    ...     date(2001, 7, 20),
    ...     date(2002, 4, 9),
    ... ], 'Test values')
    Traceback (most recent call last):
        ...
    AssertionError: Test values not in chronological order; 2002-01-16 listed before 2001-07-20
    >>> assert_chrono_order([
    ...     date(2001, 4, 17),
    ...     date(2002, 1, 16),
    ...     True,
    ...     None,
    ...     date(2001, 7, 20),
    ...     date(2002, 4, 9),
    ... ], 'Test values')
    Traceback (most recent call last):
        ...
    AssertionError: Test values not in chronological order; 2002-01-16 listed before 2001-07-20
    """
    prev = None
    for d in dates:
        if isinstance(prev, date) and isinstance(d, date):
            assert prev <= d, (
                f"{description} not in chronological order;"
                f" {prev:%Y-%m-%d} listed before {d:%Y-%m-%d}"
            )
        if isinstance(d, date):
            prev = d


def downgrade(data):
    return {
        "version_release_dates": remap_vals(
            data["cpython"]["release_dates"], {True: None}
        ),
        "series_eol_dates": remap_vals(data["cpython"]["eol_dates"], {False: None}),
    }


def remap_vals(data, remapping):
    return {k: remapping.get(v, v) for k, v in data.items()}


if __name__ == "__main__":
    main()
