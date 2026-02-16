from datetime import timedelta

from django.core.exceptions import ValidationError

PUBLIC_SLOT_DURATION_MINUTES = 30
PUBLIC_START_HOUR = 10
PUBLIC_END_HOUR = 18
PUBLIC_ALLOWED_MINUTES = {0, 30}


def calculate_end_time(start_dt, duration_minutes: int):
    return start_dt + timedelta(minutes=duration_minutes)


def validate_duration_minutes(duration_minutes: int) -> None:
    if duration_minutes is None:
        raise ValidationError('Duration is required.')
    if duration_minutes <= 0:
        raise ValidationError('Duration must be greater than 0 minutes.')


def validate_public_booking_window(start_dt, duration_minutes: int) -> None:
    """
    Public booking contract used by frontend:
    - 30-minute duration
    - half-hour boundaries
    - start times between 10:00 and 17:30 (last slot ends at 18:00)
    """
    if duration_minutes != PUBLIC_SLOT_DURATION_MINUTES:
        raise ValidationError('Public booking slots must be exactly 30 minutes.')

    if start_dt.minute not in PUBLIC_ALLOWED_MINUTES:
        raise ValidationError('Public booking slots must start on a 30-minute boundary.')

    hour = start_dt.hour
    if hour < PUBLIC_START_HOUR or hour >= PUBLIC_END_HOUR:
        raise ValidationError('Time slots must be between 10:00 AM and 6:00 PM PST.')


def find_overlapping_timeslot(start_dt, duration_minutes: int, exclude_id=None):
    from ..models import TimeSlot

    end_dt = calculate_end_time(start_dt, duration_minutes)
    candidates = TimeSlot.objects.filter(time__lt=end_dt)
    if exclude_id is not None:
        candidates = candidates.exclude(pk=exclude_id)

    for slot in candidates:
        slot_end = calculate_end_time(slot.time, slot.duration_minutes)
        if slot_end > start_dt:
            return slot

    return None
