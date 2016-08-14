"""
Mako renderer for templates.
"""
import posixpath

from mako import exceptions
from mako.util import to_list
from mako.lookup import TemplateLookup
from mako.template import Template

from kyoukai.renderers.base import Renderer


class MakoRenderer(Renderer):
    """
    A renderer that uses the Mako templating engine.

    :ivar environment: The global environment for this renderer.
        This is passed into the template renderer every time.
    """

    def __init__(self, lookup_directories: list = None):
        # Template lookup, which is accessed via a setting property.
        self._lookup = None

        # Lookup path.
        if not lookup_directories:
            self._lookup_directories = ['templates']
        else:
            self._lookup_directories = lookup_directories

        # Global environment.
        self.environment = {}

    @property
    def template_lookup(self) -> TemplateLookup:
        """
        :return: The :class:`mako.lookup.TemplateLookup` for this renderer.
        """
        if self._lookup is None:
            self._lookup = TemplateLookup(directories=self._lookup_directories,
                                          module_directory='/tmp/mako_modules')
        return self._lookup

    @template_lookup.setter
    def template_lookup(self, val):
        self._lookup = val

    def add_template_directories(self, *directories):
        """
        Adds a directories to the lookup paths for the templates.
        :param directories: The directories to add.
        """
        lookup = self.template_lookup
        # Process the directories to be "mako compatible."
        dirs = [posixpath.normpath(d) for d in to_list(directories, ())]
        lookup.directories += dirs

    def get_template(self, filename) -> Template:
        """
        Gets a :class:`mako.template.Template` object from the specified filename.

        :param filename: The filename of the template to retrieve.
        :return: The template returned from the disk.
        """
        # Find the template using the lookup.
        return self.template_lookup.get_template(filename)

    def render(self, filename, handle_exceptions=False, **kwargs) -> str:
        """
        Render a new template using Mako.

        :param filename: The filename of the template to lookup and render.
        :param handle_exceptions: Should a rendered error template be returned in case of an exception?
        :param kwargs: The keyword arguments to pass to the renderer.
        :return: The rendered template, in string format.
        """
        template = self.get_template(filename)
        try:
            to_pass = {**self.environment, **kwargs}
            return template.render(**to_pass)
        except Exception as e:
            if not handle_exceptions:
                raise
            else:
                # Render the error template.
                return exceptions.text_error_template().render()
