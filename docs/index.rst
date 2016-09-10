Kyōkai (境界)
=============

About
-----

*Kyōkai* is a fast asynchronous Python server-side web microframework.
It is built upon :mod:`asyncio` and `Asphalt`_ for an easy to use web server.

Kyōkai is Flask inspired; it attempts to be as simple as possible, but
without underlying magic to make it confusing.

Installation
------------

Kyōkai depends heavily on the asyncio library provided by Python3.4+,
and certain language features added in Python 3.5. This means the
library is not compatible with code that does not use Python 3.5 or
above.

Kyōkai is shipped as a PyPI package, so can be installed easily with
pip.

::

    $ pip install kyoukai

Alternatively, if you want cutting edge, you can install directly from
git.

::

    $ pip install git+https://github.com/SunDwarf/Kyoukai.git

**Note that the Git version is not guarenteed to be stable, at all.**

Contents:
=========

.. toctree::
   :maxdepth: 2

   gettingstarted.rst
   asphalt.rst
   routing.rst
   errorhandling.rst
   blueprints.rst

   apireference.rst
   changelog.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _Asphalt: http://asphalt.readthedocs.io/
