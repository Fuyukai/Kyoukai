.. _hostmatching:

Host Matching
=============

.. versionadded:: 2.1.3

Kyoukai comes with built-in support for Werkzeug host matching:

.. code-block:: python

    # enable host matching in the tree
    # this needs to be set on the root blueprint for the blueprint tree
    app = Kyoukai("my_website", host_matching=True)

    # set a host on a sub-blueprint
    # all sub-blueprints of `bp` will now use the host `api.myname.me`
    bp = Blueprint("api", host="api.myname.me")

As shown above, host matching is easy to enable, requiring only two changes.

  - ``host_matching`` MUST be set on the root Blueprint (passed here via the app) - this will
    enable host matching when building the final map.

  - ``host`` is passed into the Blueprint constructor, which specifies the host that will be
    matched for each route in this Blueprint.

In the example above, all routes registered to ``bp`` will only match if the Host header is
``api.myname.me``. However, all routes registered to other Blueprints will match on **any** hosts.

Relation to the Tree
--------------------

Children Blueprints will copy their host from the parent, unless overridden. So, for example:

.. code-block:: python

    # only host match ``myname.me``
    app = Kyoukai("my_website", host="myname.me")

    # bp1 will only obey requests from `myname.me`
    bp1 = Blueprint("something")
    app.register_blueprint(bp1)

    # bp2 will only obey requests from `something.myname.me`, overriding the global host match
    bp2 = Blueprint("something else", host="something.myname.me")
    app.register_blueprint(bp2)

    # bp3 however will inherit its parents host matching (bp2)
    bp3 = Blueprint("something finally")
    bp2.add_child(bp3)
