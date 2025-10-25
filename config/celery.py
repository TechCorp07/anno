"""
Celery configuration for MRI Training Platform
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

# Load config from Django settings with CELERY namespace
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Periodic tasks schedule
app.conf.beat_schedule = {
    'cleanup-proctoring-data-daily': {
        'task': 'assessment.tasks.cleanup_proctoring_data',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'detect-plagiarism-daily': {
        'task': 'assessment.tasks.detect_plagiarism',
        'schedule': crontab(hour=3, minute=0),  # 3 AM daily
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')