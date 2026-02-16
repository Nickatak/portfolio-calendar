from __future__ import annotations

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import TimeSlot
from .services.appointment_events import publish_timeslot_created_event


@receiver(post_save, sender=TimeSlot)
def publish_timeslot_created_signal(
    sender,
    instance: TimeSlot,
    created: bool,
    **kwargs,
) -> None:
    _ = (sender, kwargs)
    if not created:
        return

    # Publish only after DB commit so consumers never observe rolled-back rows.
    transaction.on_commit(lambda: publish_timeslot_created_event(instance))
