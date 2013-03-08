from django.views.generic.base import TemplateView
from django.http import HttpResponse
import json
from github_to_html import models

class JSONResponseMixin(object):
    """
    A mixin that can be used to render a JSON response.
    """
    response_class = HttpResponse

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a JSON response, transforming 'context' to make the payload.
        """
        response_kwargs['content_type'] = 'application/json'
        return self.response_class(
            self.convert_context_to_json(context),
            **response_kwargs
        )

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)

class GithubToHtmlMixin(object):
    def get_context_data(self, paths, **kwargs):
        paths = paths.strip('/').split('/')
        html = models.get_html_from_path(paths)
        # ignore kwargs
        context = {
            'title': paths[-1],
            'html': html
        }
        return context

class JSONGithubToHtmlView(JSONResponseMixin, GithubToHtmlMixin, TemplateView):
    pass

class HtmlGithubToHtmlView(GithubToHtmlMixin, TemplateView):
    template_name = 'github_to_html/github_to_html.html'
