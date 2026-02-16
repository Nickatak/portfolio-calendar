from django.db import models
from django.core.exceptions import ValidationError
from .contact import Contact


class TimeSlot(models.Model):
    """
    Represents a booked appointment slot.

    The frontend currently books 30-minute meetings, but the backend supports
    arbitrary durations for internal/admin workflows.
    """
    time = models.DateTimeField(null=False, blank=False)
    duration_minutes = models.PositiveIntegerField(default=30)
    topic = models.CharField(max_length=255, blank=True)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='timeslots', null=True)
    is_confirmed = models.BooleanField(default=False)
    is_processed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['time']

    def __str__(self):
        end_time = self._get_end_time()
        return f"{self.time} - {end_time}"

    def clean(self):
        """Validate core invariants for duration and overlap."""
        from ..services.booking_policy import find_overlapping_timeslot, validate_duration_minutes

        errors = {}

        try:
            validate_duration_minutes(self.duration_minutes)
        except ValidationError as exc:
            errors['duration_minutes'] = exc.messages

        if self.time and self.duration_minutes:
            overlap = find_overlapping_timeslot(
                start_dt=self.time,
                duration_minutes=self.duration_minutes,
                exclude_id=self.pk,
            )
            if overlap is not None:
                errors['time'] = ['Time slot overlaps with an existing appointment.']

        if errors:
            raise ValidationError(errors)

    def _get_end_time(self):
        """Calculate end time by adding appointment duration to start time."""
        from ..services.booking_policy import calculate_end_time

        return calculate_end_time(self.time, self.duration_minutes)
