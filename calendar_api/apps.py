from django.apps import AppConfig


class CalendarApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calendar_api'

    def ready(self):
        # Ensure signal handlers are registered at startup.
        from . import signals  # noqa: F401
