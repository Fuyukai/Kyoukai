"""
py.test test suite for kyoukai
"""
import json

import pytest

try:
    from http_parser.parser import HttpParser
except ImportError:
    from http_parser.pyparser import HttpParser

from kyoukai.testing.testdata import kyk


@pytest.mark.asyncio
async def test_http_10():
    response = await kyk.feed_request("GET / HTTP/1.0")
    assert response.get_response_http_version() == "1.0"
    assert response.code == 200


@pytest.mark.asyncio
async def test_http_11():
    response = await kyk.feed_request("""GET / HTTP/1.1
host: localhost

""")
    assert response.get_response_http_version() == "1.1"
    assert response.code == 200


@pytest.mark.asyncio
async def test_index():
    # Tests the index route for kyk
    response = await kyk.feed_request("""GET / HTTP/1.1
host: localhost
""")
    assert response.code == 200
    assert response.body == "OK"


@pytest.mark.asyncio
async def test_bad_http_11():
    # Tests a bad HTTP 1.1 request
    response = await kyk.feed_request("GET / HTTP/1.1\n")
    assert response.code == 400
    assert response.body == "400"


@pytest.mark.asyncio
async def test_404():
    # Tests a 404 response.
    response = await kyk.feed_request("""GET /badroute HTTP/1.1
host: localhost
""")
    assert response.code == 404
    assert response.body == "404"


@pytest.mark.asyncio
async def test_headers():
    response = await kyk.feed_request("""GET /headers HTTP/1.1
Some: TestHeader
host: localhost
""")
    assert response.headers["Some"] == "TestHeader"


@pytest.mark.asyncio
async def test_url_params():
    response = await kyk.feed_request("""GET /params?x=y&z=2 HTTP/1.1
host: localhost
""")
    assert response.headers['x'] == 'y'
    # Expected behaviour
    assert response.headers['z'] == '2'


@pytest.mark.asyncio
async def test_json_body():
    response = await kyk.feed_request("""POST /json HTTP/1.1
Content-Type: application/json
host: localhost
Content-Length: 18

{"hello": "world"}
""")
    bdy = json.loads(response.body)
    assert bdy["world"] == "hello"


@pytest.mark.asyncio
async def test_response_recalculate_headers():
    response = await kyk.feed_request("""GET / HTTP/1.1
host: localhost
    """)
    response._recalculate_headers()
    assert response.headers["Content-Length"] == 4
    assert response.headers["Content-Type"] == "text/plain"


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_bad_request():
    response = await kyk.feed_request("dhusadba")
    assert response.code == 200


@pytest.mark.asyncio
async def test_get_encoded_request():
    response = await kyk.feed_request("""GET / HTTP/1.1
host: localhost""")
    by = response.to_bytes()
    parser = HttpParser()
    parser.execute(by, len(by))

    body = parser.recv_body()
    assert body == b"OK\r\n"
