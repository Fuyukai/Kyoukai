"""
The current set of test suite data used for Kyoukai.
"""
import json

from kyoukai import HTTPRequestContext
from kyoukai import Response
from kyoukai.testing.testapp import TestingKyk

kyk = TestingKyk("")


@kyk.route("/")
async def root(ctx: HTTPRequestContext):
    return "OK"


@kyk.route("/headers")
async def headers(ctx: HTTPRequestContext):
    r = Response(body="OK", code=200)
    r.headers = ctx.request.headers
    return r


@kyk.route("/params")
async def url_params(ctx: HTTPRequestContext):
    r = Response(body="", code=204)
    for param in ctx.request.args:
        r.headers[param] = ctx.request.args[param]

    return r


@kyk.route("/json", methods=["POST"])
async def js_data(ctx: HTTPRequestContext):
    body = {}
    for key, value in ctx.request.form.items():
        body[value] = key

    return json.dumps(body), 204
