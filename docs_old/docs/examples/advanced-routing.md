# Advanced Routing

Routing in Kyōkai works based on two things:

 - Regular expressions
 - Hard matches
 
**Please note that routes are matched in the order they are defined.**
 
## Regular Expressions

*Regular Expressions* are a way to match text easily using patterns. They save expensive parsing and can be used 
easily to match web paths.

Kyōkai uses the stdlib [re](https://docs.python.org/3/library/re.html) library to match paths, so the grammar is 
exactly the same.

Here's an example that matches any path with `/numeric/<number here>`:

```python
@app.route("/numeric/[0-9]")
async def numeric(r: Request):
	return "You requested a number"
```

**Match groups are automaically extracted, and passed as parameters.**

For example, if you provide a match group for `([0-9])`:

```python
@app.route("/numeric/([0-9])")
async def numeric(r: Request, number: int):
	return "You got number: " + str(number)
```

The server will respond with:

```
$ http GET http://localhost:4444/numeric/1
HTTP/1.1 200 OK
Content-Length: 17
Content-Type: data
Date: Fri, 13 May 2016 22:01:18 -0000
Server: Kyoukai/0.2.0 (see https://github.com/SunDwarf/Kyoukai)

You got number: 1
```

## Hard Matches

In an application defined like this:

```python
@app.route("/numeric/([0-9])")
async def numeric(r: Request, number: int):
	return "You got number: " + str(number)

@app.route("/numeric/")
async def numeric_index(r: Request):
	return "You must provide a path in the form of /numeric/([0-9])!"
	
```

What happens when you request `/numeric/aa`?  
What you would expect to happen:

 - The first route is checked, sees it is not a numeric, and skipped.
 - The second route is checked, sees that it does not match, and skips it.
 - Kyōkai returns a 404.
 
What actually happens:

 - The first route is checked, sees it is not a numeric, and skipped.
 - The second route is checked, and matches it.
 
This is because Kyōkai checks that the regex matches the string partially - not entirely. This allows things such as 
custom 404 errors per route, and more powerful matches.

However, Kyōkai has a solution; *hard matches*.

A *hard match* is a match that meets the string entirely, i.e an `==` check on the path.

To define a hard match, you just need to pass an additional param to `app.route`:

```python
@app.route("/numeric/", hard_match=True)
async def numeric_index(r: Request): ...
```

That way, only the exact path `/numeric/` will match your route.
