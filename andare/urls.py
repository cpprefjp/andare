from django.conf.urls import patterns, include, url

urlpatterns = patterns('',
    url(r'^andare', include('github_to_html.urls')),
)
