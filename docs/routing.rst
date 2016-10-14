Advanced Routing
================

Routing in Kyoukai works based on regular expressions.

**Please note that routes are matched in the order they are defined.**

Regular Expressions
-------------------

*Regular Expressions* are a way to match text easily using patterns.
They save expensive parsing and can be used easily to match web paths.

Kyoukai uses the stdlib :mod:`re` library to match
paths, so the grammar is exactly the same.

Here's an example that matches any path with ``/numeric/<number here>``:

.. code:: python

    @app.route("/numeric/[0-9]")
    async def numeric(r: Request):
        return "You requested a number"

**Match groups are automaically extracted, and passed as parameters.**

For example, if you provide a match group for ``([0-9])``:

.. code:: python

    @app.route("/numeric/([0-9])")
    async def numeric(r: Request, number: int):
        return "You got number: " + str(number)

The server will respond with:

::

    $ http GET http://localhost:4444/numeric/1
    HTTP/1.1 200 OK
    Content-Length: 17
    Content-Type: data
    Date: Fri, 13 May 2016 22:01:18 -0000
    Server: Kyoukai/0.2.0 (see https://github.com/SunDwarf/Kyoukai)

    You got number: 1
