.. _deploying:

Deploying Your App
==================

Unlike some other frameworks, Kyoukai's built in web server is production ready and you do not need any specific
setup to use your web application in production.

That said, if you want to get the best performance out of Kyoukai, you need to run the app with a special flag, the
`-O` flag.

This flag is a builtin flag to the Python interpreter, and automatically skips costly `assert` statements that can
slow down your app.
This means you invoke the application with `python -O -m asphalt.core.command run config.yml`.

