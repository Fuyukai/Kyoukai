Kyōkai (境界)
-------------

|Coverage| |CircleCI|

Kyōkai is a fast asynchronous Python server-side web framework. It is
built upon `asyncio <https://docs.python.org/3/library/asyncio.html>`__
and the `Asphalt <https://github.com/asphalt-framework/asphalt>`__
framework for an extremely fast web server.

Setting up a Kyōkai app is incredibly simple. Here's a simple server
that echoes your client's headers:

.. code:: python

    import json
    from kyoukai import Kyoukai, HTTPRequestContext

    kyk = Kyoukai("example_app")

    @kyk.route("/")
    async def index(ctx: HTTPRequestContext):
        return json.dumps(request.headers), 200, {"Content-Type": "application/json"}
        
    kyk.run()

For more information, see the docs at https://mirai.veriny.tf.

.. |Coverage| image:: https://codecov.io/github/SunDwarf/Kyoukai/coverage.svg
   :target: https://codecov.io/gh/SunDwarf/Kyoukai
.. |CircleCI| image:: https://img.shields.io/circleci/project/SunDwarf/Kyoukai.svg?maxAge=2592000
   :target: https://circleci.com/gh/SunDwarf/Kyoukai/
