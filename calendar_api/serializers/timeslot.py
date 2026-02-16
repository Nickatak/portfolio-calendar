from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from ..models import TimeSlot
from ..services.booking_policy import (
    find_overlapping_timeslot,
    validate_duration_minutes,
    validate_public_booking_window,
)


class TimeSlotSerializer(serializers.ModelSerializer):
    datetime = serializers.DateTimeField(source='time', required=False)
    start_time = serializers.DateTimeField(source='time', required=False)
    end_time = serializers.DateTimeField(required=False, write_only=True)

    class Meta:
        model = TimeSlot
        fields = [
            'id',
            'topic',
            'datetime',
            'start_time',
            'duration_minutes',
            'end_time',
            'contact',
            'is_confirmed',
            'is_processed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'contact': {'required': False, 'allow_null': True},
            'duration_minutes': {'required': False},
            'is_confirmed': {'required': False},
            'is_processed': {'required': False},
        }

    def to_representation(self, instance):
        """Expose computed end_time and keep alias fields in output."""
        data = super().to_representation(instance)
        end_dt = instance._get_end_time()
        data['end_time'] = serializers.DateTimeField().to_representation(end_dt)
        return data

    def validate(self, data):
        raw_end_dt = data.pop('end_time', None)
        start_dt = data.get('time')
        duration_minutes = data.get('duration_minutes')

        if self.instance is not None:
            if start_dt is None:
                start_dt = self.instance.time
            if duration_minutes is None:
                duration_minutes = self.instance.duration_minutes

        if start_dt is None:
            return data

        if duration_minutes is None and raw_end_dt is not None:
            delta_seconds = (raw_end_dt - start_dt).total_seconds()
            if delta_seconds <= 0:
                raise serializers.ValidationError('end_time must be after start_time.')
            if delta_seconds % 60 != 0:
                raise serializers.ValidationError('Time range must align to whole minutes.')
            duration_minutes = int(delta_seconds // 60)
            data['duration_minutes'] = duration_minutes

        if duration_minutes is None:
            duration_minutes = 30
            data['duration_minutes'] = duration_minutes

        try:
            validate_duration_minutes(duration_minutes)
            if self.context.get('enforce_public_policy', False):
                validate_public_booking_window(start_dt, duration_minutes)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages)

        overlap = find_overlapping_timeslot(
            start_dt=start_dt,
            duration_minutes=duration_minutes,
            exclude_id=self.instance.pk if self.instance is not None else None,
        )
        if overlap is not None:
            raise serializers.ValidationError('Time slot overlaps with an existing appointment.')

        return data
