from django.conf.urls import patterns, include, url
from app import views

urlpatterns = patterns('',
    url(r'^/html/(?P<paths>.*)$', views.JSONGithubToHtmlView.as_view()),
    url(r'^/view/(?P<paths>.*)$', views.HtmlGithubToHtmlView.as_view()),
    url(r'^/local/(?P<paths>.*)$', views.HtmlLocalGithubToHtmlView.as_view()),
    url(r'^/contents$', views.ContentsView.as_view()),
    url(r'^/all_contents$', views.AllContentsView.as_view()),
    url(r'^/start$', views.StartView.as_view()),
    url(r'^/commit$', views.CommitView.as_view()),
    url(r'^/errors$', views.ErrorView.as_view()),
    url(r'^/oauth$', views.OAuthView.as_view()),
)
