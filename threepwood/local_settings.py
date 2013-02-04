__author__ = 'cdumitru'


from threepwood.settings.base import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'threepwood.sqlite',                      # Or path to database file if using sqlite3.
    }
}