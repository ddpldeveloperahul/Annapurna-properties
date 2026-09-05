import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "annapurna_pro.settings")

app = Celery("annapurna_pro")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(["myapp", "workers"])


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
