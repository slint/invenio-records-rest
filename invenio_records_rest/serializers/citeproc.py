# -*- coding: utf-8 -*-
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

"""CSL Citation Formatter serializer for records."""

from __future__ import absolute_import, print_function

import json
import re

from citeproc import Citation, CitationItem, CitationStylesBibliography, \
    CitationStylesStyle, formatter
from citeproc.source.bibtex import BibTeX
from citeproc.source.json import CiteProcJSON
from flask import has_request_context, request
from six import StringIO
from webargs import fields
from webargs.flaskparser import FlaskParser

from ..errors import StyleNotFoundRESTError

try:
    from citeproc_styles import get_style_filepath
    from citeproc_styles.errors import StyleNotFoundError
except:
    import warnings
    warnings.warn('citeproc_styles not found. '
                  'Please install to enable Citeproc Serialization.')


class CiteprocSerializer(object):
    """CSL Citation Formatter serializer for records.

    In order to produce a formatted citation of a record through citeproc-py,
    we need a CSL-JSON or BibTeX serialized version of it. Since there may be
    already an implementation of such a serializer, it can be passed in the
    constructor of this class. This serializer has to implement a `serialize`
    method that returns the CSL-JSON/BibTeX result.
    """

    _default_style = 'harvard1'
    """The `citeproc-py` library supports by default the 'harvard1' style."""

    _default_locale = 'en-US'
    """The `citeproc-py` library supports by default the 'en-US' locale."""

    _user_args = {
        'style': fields.Str(missing=_default_style),
        'locale': fields.Str(missing=_default_locale)
    }
    """Arguments for the webargs parser."""

    _valid_formats = ('csl', 'bibtex')
    """Supported formats by citeproc-py."""

    def __init__(self, serializer, record_format='csl'):
        """Initialize the inner record serializer.

        :param serializer: Serializer object that does the record serialization
        to a format that `citeproc-py` can process (CSL-JSON or BibTeX). The
        object has to implement a `serialize` method that matches the signature
        of the `serialize` method of this class.
        :param record_format: Format that the serializer produces
        """
        assert record_format in self._valid_formats

        assert getattr(serializer, 'serialize', None)
        assert callable(getattr(serializer, 'serialize'))

        self.serializer = serializer
        self.record_format = record_format

    @classmethod
    def _get_args(cls, **kwargs):
        """Parse style and locale.

        Argument location precedence: kwargs > view_args > query
        """
        csl_args = {
            'style': cls._default_style,
            'locale': cls._default_locale
        }

        if has_request_context():
            parser = FlaskParser(locations=('view_args', 'query'))
            csl_args.update(parser.parse(cls._user_args, request))

        csl_args.update({k: kwargs[k]
                         for k in ('style', 'locale') if k in kwargs})

        try:
            csl_args['style'] = get_style_filepath(csl_args['style'].lower())
        except StyleNotFoundError:
            if has_request_context():
                raise StyleNotFoundRESTError(csl_args['style'])
            raise
        return csl_args

    def _get_source(self, data):
        """Get source data object for citeproc-py."""
        if self.record_format == 'csl':
            return CiteProcJSON([json.loads(data)])
        elif self.record_format == 'bibtex':
            return BibTeX(StringIO(data))

    def _clean_result(self, text):
        """Remove double spaces and punctuation."""
        text = re.sub('\s\s+', ' ', text)
        text = re.sub('\.\.+', '.', text)
        return text

    def serialize(self, pid, record, links_factory=None, **kwargs):
        """Serialize a single record.

        :param pid: Persistent identifier instance.
        :param record: Record instance.
        :param links_factory: Factory function for record links.
        """
        data = self.serializer.serialize(pid, record, links_factory)
        source = self._get_source(data)
        style = CitationStylesStyle(validate=False, **self._get_args(**kwargs))
        bib = CitationStylesBibliography(style, source, formatter.plain)
        citation = Citation([CitationItem(pid.pid_value)])
        bib.register(citation)

        return self._clean_result(''.join(bib.bibliography()[0]))
