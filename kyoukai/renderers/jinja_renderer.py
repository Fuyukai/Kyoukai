"""
Jinja2 renderer for templates.
"""
from jinja2.environment import Environment, Template
# Default loader is the FileSystemLoader, contained inside a ChoiceLoader.
from jinja2.loaders import FileSystemLoader, ChoiceLoader, BaseLoader

from kyoukai.renderers.base import Renderer


class Jinja2Renderer(Renderer):
    """
    A renderer that uses the Jinja2 Rendering Engine.

    :param loader: The Loader to use for the engine to load templates from.
    """
    def __init__(self, loader: BaseLoader=None):
        self._loader = ChoiceLoader(loaders=[])

        if loader is None:
            # Use a default FileSystemLoader.
            self._loader.loaders.append(FileSystemLoader(searchpath="templates"))

        self._environment = None

    @property
    def loader(self):
        return self._loader

    @property
    def environment(self) -> Environment:
        if self._environment is None:
            self._environment = Environment(loader=self._loader)
        return self._environment

    @environment.setter
    def environment(self, env: Environment):
        self._environment = env

    def add_loader(self, loader: BaseLoader):
        """
        Adds a loader to the ChoiceLoader contained within.

        :param loader: The Loader to add.
        """
        self.loader.loaders.append(loader)

    def get_template(self, template_name: str) -> Template:
        """
        Gets a :class:`jinja2.environment.Template` from the Environment.

        :param template_name: The template to load.
        :return: The new template object.
        """
        return self.environment.get_template(template_name)

    def render(self, template_name: str, **kwargs) -> str:
        """
        Renders a template using Jinja2.

        :param template_name: The name of the template to render.
        :param kwargs: Keyword arguments to pass to the template as a dict.
        :return: A new str containing the rendered HTML of the template.
        """
        template = self.get_template(template_name)
        return template.render(**kwargs)


