#!/usr/bin/python3
__python_requires__ = '~= 3.6'
__requires__ = [
    'click ~= 7.0',
    'jsonschema ~= 3.0',
]
from   bisect      import bisect_left
from   collections import defaultdict
from   datetime    import date, datetime
import json
import click
from   jsonschema  import validate

@click.command()
@click.argument('data_file', type=click.File())
@click.argument('schema_file', type=click.File())
def main(data_file, schema_file):
    """
    Perform various validations and sanity checks on pyversion-info-data.json
    """
    with data_file:
        data = json.load(data_file)
    with schema_file:
        schema = json.load(schema_file)

    # Check that data conforms to schema
    validate(data, schema)

    versions = [
        (parse_version(v), parse_date(d))
        for v,d in data["version_release_dates"].items()
    ]
    versions.sort()

    major2minors = defaultdict(set)
    for series in data["series_eol_dates"].keys():
        x,y = parse_version(series)
        major2minors[x].add(y)

    # Check that each series has one or more micro versions
    for series in data["series_eol_dates"].keys():
        assert get_micro_versions(versions, parse_version(series)), \
            f'Series {series} present but does not have any versions'

    # Check that each micro version belongs to a series
    for v,_ in versions:
        s = unparse_version(v[:2])
        assert s in data["series_eol_dates"], \
            f'Version {unparse_version(v)} present but series {s} missing'

    # Check that all major versions form a set {0..n}
    assert_Zn(major2minors.keys(), 'Major versions')

    # Check that, for each major version other than 0, the minor versions form
    # a set {0..n}
    for major, minors in major2minors.items():
        if major != 0:
            assert_Zn(minors, f'Minor versions of v{major}')

    # Check that, for each minor version other than 0.Y, the micro versions
    # form a set {0..n}
    for series in data["series_eol_dates"].keys():
        vseries = parse_version(series)
        if vseries[0] != 0:
            micros = [z for (_,_,z),_ in get_micro_versions(versions, vseries)]
            assert_Zn(micros, f'Micro versions of v{series}')

    # Check that the major versions' first releases are in chronological order
    first_releases = []
    for major in major2minors.keys():
        first_v, first_date = versions[bisect_left(versions, ((major,), None))]
        assert first_v[0] == major
        first_releases.append(first_date)
    assert_chrono_order(first_releases, 'Initial releases of major versions')

    # Check that, for each major version, the minor versions' first releases
    # are in chronological order
    for major, minors in major2minors.items():
        first_releases = []
        for m in minors:
            first_v, first_date \
                = versions[bisect_left(versions, ((major, m), None))]
            assert first_v[:2] == (major, m)
            first_releases.append(first_date)
        assert_chrono_order(first_releases,
                            f'Initial releases of minor versions of v{major}')

    # Check that each minor version's micro releases are in chronological order
    for series in data["series_eol_dates"].keys():
        releases = [
            d for _,d in get_micro_versions(versions, parse_version(series))
        ]
        assert_chrono_order(releases, f'Micro releases of {series}')

    # Check that no micro versions are released after a series goes EOL
    # (Apparently, this can legitimately happen; see v3.0.
    #for series, eol_date in data["series_eol_dates"].items():
    #    if isinstance(eol_date, str):
    #        eol_date = parse_date(eol_date)
    #        for v, rel in get_micro_versions(versions, parse_version(series)):
    #            assert rel is None or rel <= eol_date, \
    #                f'Version {unparse_version(v)} released after series EOL'

def get_micro_versions(versions, series):
    """
    >>> versions = [
    ...     ((2,0,0), date(2000,10,16)),
    ...     ((2,0,1), date(2001, 6,22)),
    ...     ((2,1,0), date(2001, 4,17)),
    ...     ((2,1,1), date(2001, 7,20)),
    ...     ((2,1,2), date(2002, 1,16)),
    ...     ((2,1,3), date(2002, 4, 9)),
    ...     ((2,2,0), date(2001,12,21)),
    ...     ((2,2,1), date(2002, 4,10)),
    ...     ((2,2,2), date(2002,10,14)),
    ...     ((2,2,3), date(2003, 5,30)),
    ... ]
    >>> get_micro_versions(versions, (1,9))
    []
    >>> get_micro_versions(versions, (2,0))
    [((2, 0, 0), datetime.date(2000, 10, 16)), ((2, 0, 1), datetime.date(2001, 6, 22))]
    >>> get_micro_versions(versions, (2,1))
    [((2, 1, 0), datetime.date(2001, 4, 17)), ((2, 1, 1), datetime.date(2001, 7, 20)), ((2, 1, 2), datetime.date(2002, 1, 16)), ((2, 1, 3), datetime.date(2002, 4, 9))]
    >>> get_micro_versions(versions, (2,2))
    [((2, 2, 0), datetime.date(2001, 12, 21)), ((2, 2, 1), datetime.date(2002, 4, 10)), ((2, 2, 2), datetime.date(2002, 10, 14)), ((2, 2, 3), datetime.date(2003, 5, 30))]
    >>> get_micro_versions(versions, (2,3))
    []
    """
    x,y = series
    return versions[
        bisect_left(versions, (series, None))
        : bisect_left(versions, ((x, y+1), None))
    ]

def parse_version(s):
    return tuple(map(int, s.split('.')))

def unparse_version(v):
    return '.'.join(map(str, v))

def parse_date(s):
    if isinstance(s, str):
        return datetime.strptime(s, '%Y-%m-%d').date()
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
    assert not diff, f'{description} not contiguous; missing {min(diff)}'

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
            assert prev <= d, \
                f'{description} not in chronological order;'\
                f' {prev:%Y-%m-%d} listed before {d:%Y-%m-%d}'
        if isinstance(d, date):
            prev = d

if __name__ == '__main__':
    main()
