#coding: utf-8
import json
from django.views.generic.base import View, TemplateView
from django.http import HttpResponse, HttpResponseRedirect
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
        content = models.get_html_content_by_path(paths)
        # ignore kwargs
        context = {
            'title': content['title'],
            'html': content['html']
        }
        return context

class JSONGithubToHtmlView(JSONResponseMixin, GithubToHtmlMixin, TemplateView):
    pass

class HtmlGithubToHtmlView(GithubToHtmlMixin, TemplateView):
    template_name = 'github_to_html/github_to_html.html'

class ContentsView(JSONResponseMixin, TemplateView):
    def get_context_data(self, **kwargs):
        contents = models.get_update_contents()

        context = {
            "contents": contents
        }
        return context

class StartView(JSONResponseMixin, View):
    def get_context_data(self, **kwargs):
        context = {
            "success": True,
        }
        context.update(kwargs)
        return context

    def post(self, request, *args, **kwargs):
        message = models.git_fetch(settings.GIT_REMOTE)
        print message
        models.git_checkout(settings.GIT_LOCAL_FETCHED)
        message = models.git_merge(settings.GIT_REMOTE_BRANCH)
        print message
        context = self.get_context_data(message=message)
        return self.render_to_response(context)

class CommitView(JSONResponseMixin, View):
    def get_context_data(self, **kwargs):
        context = {
            "success": True,
        }
        context.update(kwargs)
        return context

    def post(self, request, *args, **kwargs):
        models.git_checkout(settings.GIT_LOCAL_BRANCH)
        message = models.git_merge(settings.GIT_LOCAL_FETCHED)
        print message
        models.git_checkout(settings.GIT_LOCAL_FETCHED)

        context = self.get_context_data(message=message)
        return self.render_to_response(context)

class OAuthView(View):
    # GET https://github.com/login/oauth/authorize?client_id=5163f9957aabe66d2ce4
    def get(self, request):
        code = request.GET.get('code')
        models.set_access_token(code)

        return HttpResponseRedirect('https://github.com/cpprefjp/site')
