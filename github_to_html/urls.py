from django.conf.urls import patterns, include, url
from github_to_html import views

urlpatterns = patterns('',
    url(r'^/html/(?P<paths>.*)$', views.JSONGithubToHtmlView.as_view()),
    url(r'^/view/(?P<paths>.*)$', views.HtmlGithubToHtmlView.as_view()),
    url(r'^/contents$', views.ContentsView.as_view()),
    url(r'^/start$', views.StartView.as_view()),
    url(r'^/commit$', views.CommitView.as_view()),
    url(r'^/errors$', views.ErrorView.as_view()),
    url(r'^/oauth$', views.OAuthView.as_view()),
)
