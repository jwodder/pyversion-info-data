.. image:: http://www.repostatus.org/badges/latest/active.svg
    :target: http://www.repostatus.org/#active
    :alt: Project Status: Active — The project has reached a stable, usable
          state and is being actively developed.

.. image:: https://github.com/jwodder/pyversion-info-data/actions/workflows/validate.yml/badge.svg
    :target: https://github.com/jwodder/pyversion-info-data/actions/workflows/validate.yml
    :alt: CI Status

.. image:: https://img.shields.io/github/license/jwodder/pyversion-info-data.svg
    :target: https://creativecommons.org/publicdomain/zero/1.0/
    :alt: Creative Commons Zero v1.0 Universal

This repository contains the databases of CPython and PyPy version information
that are queried by the `pyversion-info
<https://pypi.org/project/pyversion-info/>`_ Python library in order to provide
up-to-date information about supported & historic Python versions — namely,
what versions exist/have been announced, when they were or will be released,
CPython series end-of-life dates, and CPython versions corresponding to each
PyPy release.

I promise 24-hour turnaround times for keeping the database up-to-date until I
am hit by a bus.

Files
=====

``pyversion-info-data.json``
    The database used by v0.x of ``pyversion-info``, containing only
    information on CPython releases.

``pyversion-info-data.schema.json``
    The JSON Schema for ``pyversion-info-data.json``

``pyversion-info-data.v1.json``
    The database used by v1.x of ``pyversion-info``, containing information on
    both CPython and PyPy

``pyversion-info-data.v1.schema.json``
    The JSON Schema for ``pyversion-info-data.v1.json``

``manage.py``
    A utility script for updating the databases

``validate.py``
    A script for validating and sanity-checking the databases
