from __future__ import annotations

import logging
from typing import Any, Callable
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from ..models import TimeSlot

logger = logging.getLogger(__name__)


def publish_timeslot_created_event(timeslot: TimeSlot) -> dict[str, Any] | None:
    """Publish one appointment-created event for a newly created timeslot."""
    if not settings.KAFKA_PRODUCER_ENABLED:
        return None

    payload = build_timeslot_created_payload(timeslot)
    if payload is None:
        return None

    publish_fn = _import_publish_function()
    if publish_fn is None:
        return None

    try:
        metadata = publish_fn(payload)
    except Exception:
        logger.exception(
            "Kafka publish failed for timeslot_id=%s contact_id=%s",
            timeslot.id,
            timeslot.contact_id,
        )
        return None

    logger.info(
        "Kafka publish succeeded for timeslot_id=%s topic=%s partition=%s offset=%s",
        timeslot.id,
        metadata.get("topic"),
        metadata.get("partition"),
        metadata.get("offset"),
    )
    return metadata


def build_timeslot_created_payload(timeslot: TimeSlot) -> dict[str, Any] | None:
    """Build notifier payload for appointments.created."""
    contact = timeslot.contact
    if contact is None:
        logger.info("Kafka publish skipped for timeslot_id=%s: no contact", timeslot.id)
        return None

    email = (contact.email or "").strip()
    if not email:
        logger.info("Kafka publish skipped for timeslot_id=%s: missing contact email", timeslot.id)
        return None

    phone_raw = (contact.phone_number or "").strip()
    phone_e164 = phone_raw if _is_e164_phone(phone_raw) else None

    notify_email = bool(settings.KAFKA_NOTIFY_EMAIL_DEFAULT)
    notify_sms = bool(settings.KAFKA_NOTIFY_SMS_DEFAULT and phone_e164)

    appointment: dict[str, Any] = {
        "appointment_id": f"timeslot-{timeslot.id}",
        "user_id": str(contact.id),
        "start_time": timeslot.time.isoformat(),
        "end_time": timeslot._get_end_time().isoformat(),
        "duration_minutes": timeslot.duration_minutes,
        # Backward-compatible alias retained for downstream consumers not yet migrated.
        "time": timeslot.time.isoformat(),
        "email": email,
    }
    if phone_e164 is not None:
        appointment["phone_e164"] = phone_e164

    return {
        "event_id": f"evt-{uuid4()}",
        "event_type": "appointments.created",
        "occurred_at": timezone.now().isoformat(),
        "notify": {
            "email": notify_email,
            "sms": notify_sms,
        },
        "appointment": appointment,
    }


def _import_publish_function() -> Callable[[dict[str, Any]], dict[str, Any]] | None:
    """Resolve notifier Kafka publish function at runtime."""
    try:
        from notifications.adapters.kafka_runtime import publish_appointment_created_event
    except Exception as exc:
        logger.warning(
            "Notifier producer library unavailable. "
            "Install `kafka-notifications-lib` to enable Kafka publishing. error=%s",
            exc,
        )
        return None
    return publish_appointment_created_event


def _is_e164_phone(value: str) -> bool:
    if not value.startswith("+"):
        return False
    digits = value[1:]
    return digits.isdigit() and 8 <= len(digits) <= 15
