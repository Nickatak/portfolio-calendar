from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from calendar_api.models.settings import Settings


class Command(BaseCommand):
    help = "Seed development data (idempotent)."

    def handle(self, *args, **options):
        user_model = get_user_model()
        email = "test@ex.com"
        username = "test"
        password = "Qweqwe123"

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        changed = False
        if user.email != email:
            user.email = email
            changed = True
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if not user.check_password(password):
            user.set_password(password)
            changed = True

        if created or changed:
            user.save()

        settings_obj, _ = Settings.objects.get_or_create(user=user)

        action = "created" if created else "updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"Development seed {action}: {user.username} ({user.email}), settings_id={settings_obj.id}"
            )
        )
