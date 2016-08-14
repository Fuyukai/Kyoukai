"""
The Base renderer is a simple ABC which children renderers inherit from and override.
"""
import abc


class Renderer:
    @abc.abstractmethod
    def get_template(self, template_name: str):
        """
        Gets a template from the rendering environment.

        :param template_name: The path to the template.
        :return: The Template object for the respective Renderer.
        """

    @abc.abstractmethod
    def render(self, template_name: str, **kwargs) -> str:
        """
        Renders a template out into a HTML string.

        :param template_name: The name of the template to use.
        :param kwargs: Keyword arguments to pass into the renderer.
        :return: A new :class:`str` which is the output of the renderer.
        """
