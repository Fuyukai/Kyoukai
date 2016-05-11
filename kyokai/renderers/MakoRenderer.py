import mako.lookup

# Create a lookup that uses /templates and /tmp/mako_modules to store cached data.
kyokai_templates = mako.lookup.TemplateLookup(directories=['templates'], module_directory='/tmp/mako_modules')


def render(filename, **kwargs):
    """
    Render a file using Mako.

    Passes all of the keyword arguments to the template renderer.
    """
    template = kyokai_templates.get_template(filename)
    return template.render(**kwargs)