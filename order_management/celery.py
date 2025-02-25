"""Celery module
"""

from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "order_management.settings")

app = Celery("order_management")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatically discover tasks in your installed apps.
app.autodiscover_tasks()

# Add the new setting to suppress the warning and ensure compatibility with Celery 6.0+
app.conf.broker_connection_retry_on_startup = True


@app.task(bind=True)
def debug_task(self):
    """Debug task to check Celery configuration."""
    print(f"Request: {self.request!r}")
