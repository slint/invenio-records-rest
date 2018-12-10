# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""Python 2/3 compatibility utliities."""

import functools
import inspect
import sys

PY2 = int(sys.version_info[0]) == 2
if PY2:
    def _get_args(func):
        return inspect.getargspec(func).args
else:
    def _get_args(func):
        return inspect.signature(func).parameters


def get_func_args(func):
    """Get a list of the arguments a function or method has."""
    if isinstance(func, functools.partial):
        return get_func_args(func.func)

    if inspect.isfunction(func) or inspect.ismethod(func):
        return list(_get_args(func))
    if callable(func):
        return list(_get_args(func.__call__))
