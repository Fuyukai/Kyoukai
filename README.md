## Kyōkai (境界)

**This project will not be getting any more updates.**

[![Coverage](https://codecov.io/github/SunDwarf/Kyoukai/coverage.svg)](https://codecov.io/gh/SunDwarf/Kyoukai)
[![CircleCI](https://img.shields.io/circleci/project/SunDwarf/Kyoukai.svg?maxAge=2592000)](https://circleci.com/gh/SunDwarf/Kyoukai/)

Kyōkai is a fast asynchronous Python server-side web framework. It is built upon
[asyncio](https://docs.python.org/3/library/asyncio.html) and the
[Asphalt](https://github.com/asphalt-framework/asphalt) framework for an extremely fast web server.

Setting up a Kyōkai app is incredibly simple. Here's a simple server that echoes your client's headers:

```python
import json
from kyoukai import Kyoukai, HTTPRequestContext

kyk = Kyoukai("example_app")

@kyk.route("/")
async def index(ctx: HTTPRequestContext):
    return json.dumps(dict(ctx.request.headers)), 200, {"Content-Type": "application/json"}
    
kyk.run()
```

For more information, see the docs at https://mirai.veriny.tf.
