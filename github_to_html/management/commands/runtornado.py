import os
import sys
from tornado import httpserver, wsgi, ioloop
import django
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    def handle(self, port='', *args, **options):
        if port == '':
            port = '8080'

        sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
        sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)

        print "Validating models..."
        self.validate(display_num_errors=True)
        print "\nDjango version %s, using settings %r" % (django.get_version(), settings.SETTINGS_MODULE)
        print "Server is running at http://%s:%s/" % ('*', port)

        application = get_wsgi_application()
        container = wsgi.WSGIContainer(application)
        http_server = httpserver.HTTPServer(container)
        http_server.listen(int(port), address='*')
        ioloop.IOLoop.instance().start()
