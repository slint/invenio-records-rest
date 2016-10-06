# -*- coding: utf-8 -*-#
#
# This file is part of Invenio.
# Copyright (C) 2016 CERN.
#
# Invenio is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307, USA.
#
# In applying this license, CERN does not
# waive the privileges and immunities granted to it by virtue of its status
# as an Intergovernmental Organization or submit itself to any jurisdiction.

"""Citeproc serializer tests."""

from __future__ import absolute_import, print_function

import json

import pytest
from invenio_pidstore.models import PersistentIdentifier
from invenio_records import Record

from invenio_records_rest.errors import StyleNotFoundRESTError
from invenio_records_rest.serializers.citeproc import CiteprocSerializer, \
    StyleNotFoundError


def get_test_data():
    pid = PersistentIdentifier(pid_type='recid', pid_value='1')
    record = Record({
        'title': 'Citeproc test', 'type': 'book',
        'creators': [
            {'family_name': 'Doe', 'given_name': 'John'},
            {'family_name': 'Smith', 'given_name': 'Jane'}
        ],
        'publication_date': [2016, 1, 1]
    })
    return pid, record


class TestCslJsonSerializer(object):
    """Test CSL JSON Serializer."""

    def serialize(self, pid, record, links_factory=None):
        csl_json = {}
        csl_json['id'] = pid.pid_value
        csl_json['type'] = record['type']
        csl_json['title'] = record['title']
        csl_json['author'] = [{'family': a['family_name'],
                               'given': a['given_name']}
                              for a in record['creators']]
        csl_json['issued'] = {'date-parts': [record['publication_date']]}
        return json.dumps(csl_json)


class TestBibTexSerializer(object):
    """Test BibTex Serializer."""

    def serialize(self, pid, record, links_factory=None):
        bibtex_template = (
            '@{type}{{{id},'
            '  author = {{{authors}}},'
            '  title  = {{{{{title}}}}},'
            '  year   = {year},'
            '}}'
        )

        result = bibtex_template.format(
            id=pid.pid_value,
            type=record['type'],
            authors=', '.join([' '.join((a['given_name'], a['family_name']))
                               for a in record['creators']]),
            title=record['title'],
            year=record['publication_date'][0],
        )
        return result


def test_csl_serialization():
    """Test CSL Citeproc serialization."""
    pid, record = get_test_data()

    serializer = CiteprocSerializer(TestCslJsonSerializer())
    data = serializer.serialize(pid, record)
    assert 'Citeproc test' in data
    assert 'Doe, J.' in data
    assert '& Smith, J.' in data
    assert '2016.' in data


def test_bibtex_serialization():
    """Test BibTex Citeproc serialization."""
    pid, record = get_test_data()

    serializer = CiteprocSerializer(TestBibTexSerializer(), 'bibtex')
    data = serializer.serialize(pid, record)
    assert 'Citeproc test' in data
    assert 'John Doe, J.S.,' in data
    assert '2016.' in data


def test_serializer_args():
    """Test Citeproc serialization arguments."""
    pid, record = get_test_data()

    serializer = CiteprocSerializer(TestCslJsonSerializer())
    data = serializer.serialize(pid, record, style='science')
    assert '1.' in data
    assert 'J. Doe,' in data
    assert 'J. Smith,' in data
    assert 'Citeproc test' in data
    assert '(2016)' in data


def test_nonexistent_style():
    """Test Citeproc exceptions."""
    pid, record = get_test_data()

    serializer = CiteprocSerializer(TestCslJsonSerializer())
    with pytest.raises(StyleNotFoundError):
        serializer.serialize(pid, record, style='non-existent')


def test_serializer_in_request(app):
    """Test Citeproc serialization while in a request context."""
    pid, record = get_test_data()

    serializer = CiteprocSerializer(TestCslJsonSerializer())

    with app.test_request_context(query_string={'style': 'science'}):
        data = serializer.serialize(pid, record)
        assert '1.' in data
        assert 'J. Doe,' in data
        assert 'J. Smith,' in data
        assert 'Citeproc test' in data
        assert '(2016)' in data

    with app.test_request_context(query_string={'style': 'non-existent'}):
        with pytest.raises(StyleNotFoundRESTError):
            serializer.serialize(pid, record, style='non-existent')
