"""
py.test test suite for kyoukai
"""
import pytest
from werkzeug.wrappers import Response

from kyoukai import __version__
from kyoukai.asphalt import HTTPRequestContext
from kyoukai.blueprint import Blueprint
from kyoukai.testing import TestKyoukai
from kyoukai.util import wrap_response
from kyoukai.wsgi import to_wsgi_environment, get_formatted_response

app = TestKyoukai("kyoukai_test")


# finalize
app.finalize()


def test_route_adding():
    with app.testing_bp() as bp:
        # fake route
        def _inner(ctx: HTTPRequestContext):
            pass

        rtt = bp.wrap_route(_inner)
        assert rtt.get_endpoint_name(bp) == bp.name + "._inner"

        rtt = bp.add_route(rtt, "/")
        bp.finalize()
        assert bp.finalized
        assert len(bp.routes) == 1

        # test matching of the route
        environ = to_wsgi_environment({}, "GET", "/", "1.1")
        environ["SERVER_NAME"] = ""
        environ["SERVER_PORT"] = "4444"
        assert bp.match(environ)[0] == rtt

    assert len(app.root.routes) == 0


@pytest.mark.asyncio
async def test_basic_request():
    """
    Tests a basic GET request to /.
    """
    with app.testing_bp() as bp:
        @bp.route("/")
        def root(ctx: HTTPRequestContext):
            return Response("Hello, world!")

        r = await app.inject_request({}, "/")
        assert r.data == b"Hello, world!"


@pytest.mark.asyncio
async def test_basic_post():
    """
    Tests a basic POST request to /.
    """
    with app.testing_bp() as bp:
        @bp.route("/", methods=["POST"])
        def root_body(ctx: HTTPRequestContext):
            body = ctx.request.data
            return Response(body[::-1])

        r = await app.inject_request({}, "/", body="!dlrow ,olleH", method="POST")
        assert r.data == b"Hello, world!"


def test_wrap_response():
    """
    Tests wrapping a Response object.
    """
    r1 = wrap_response(("Hello, world!",))
    assert r1.data == b"Hello, world!"
    assert r1.status_code == 200

    r2 = wrap_response(("a", 204))
    assert r2.data == b"a"
    assert r2.status_code == 204

    r3 = wrap_response(("a", 401, {"Content-Type": "application/json"}))  # weird json
    assert r3.data == b"a"
    assert r3.status_code == 401
    assert r3.headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_get_formatted_response():
    """
    Tests getting a formatted werkzeug Response.
    """
    with app.testing_bp() as bp:
        @bp.route("/")
        def root(ctx: HTTPRequestContext):
            return Response("Hello, world!")

        r = await app.inject_request({}, "/")

        environ = to_wsgi_environment({}, "GET", "/", "1.1")
        response = get_formatted_response(r, environ)

        # Pre-built response
        assert response == b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: ' \
                           b'13\r\nServer: Kyoukai/%s\r\n\r\nHello, world!' % __version__.encode()



