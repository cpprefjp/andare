from django.conf.urls import patterns, include, url
from github_to_html.views import GithubToHtmlView

urlpatterns = patterns('',
    url(r'^/html/(?P<paths>.*)$', GithubToHtmlView.as_view()),
)
