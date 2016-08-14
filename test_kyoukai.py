"""
py.test test suite for kyoukai
"""

import pytest

from kyoukai import HTTPRequestContext
from kyoukai.testing.testapp import TestingKyk

kyk = TestingKyk("")


@kyk.route("/")
async def root(ctx: HTTPRequestContext):
    return "OK"


@pytest.mark.asyncio
async def test_index():
    # Tests the index route for kyk
    response = await kyk.feed_request("""GET / HTTP/1.1
host: localhost
""")
    assert response.code == 200
    assert response.body == "OK"
