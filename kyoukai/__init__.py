"""
Kyoukai is an async web framework for Python 3.5 and above.
"""
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.formparser import FormDataParser
import json


def _parse_json(parser: FormDataParser, stream, mimetype, content_length, options):
    if parser.max_content_length is not None and \
                    content_length is not None and \
                    content_length > parser.max_content_length:
        raise RequestEntityTooLarge()

    # json loads the stream and return it
    return stream, json.load(stream), {}


FormDataParser.parse_functions["application/json"] = _parse_json

from kyoukai.app import Kyoukai, __version__
from kyoukai.blueprint import Blueprint
from kyoukai.route import Route
from kyoukai.testing import TestKyoukai
