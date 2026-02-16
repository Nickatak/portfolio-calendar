from datetime import datetime
from unittest import mock

from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from .models import Contact, TimeSlot


def aware_dt(year, month, day, hour, minute=0, second=0):
    return timezone.make_aware(datetime(year, month, day, hour, minute, second), timezone.get_current_timezone())


class HealthCheckTests(APITestCase):
    def test_healthz(self):
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'ok'})


class TimeSlotModelTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(
            first_name='John',
            last_name='Doe',
            email='john@example.com',
        )

    def test_default_duration_is_30_minutes(self):
        timeslot = TimeSlot(
            time=aware_dt(2026, 1, 27, 10, 0),
            topic='Morning Meeting',
            contact=self.contact,
        )
        timeslot.full_clean()
        timeslot.save()

        self.assertEqual(timeslot.duration_minutes, 30)
        self.assertEqual(timeslot._get_end_time(), aware_dt(2026, 1, 27, 10, 30))

    def test_custom_duration_changes_end_time(self):
        timeslot = TimeSlot(
            time=aware_dt(2026, 1, 27, 14, 0),
            duration_minutes=60,
            topic='Deep Dive',
            contact=self.contact,
        )
        timeslot.full_clean()
        timeslot.save()

        self.assertEqual(timeslot._get_end_time(), aware_dt(2026, 1, 27, 15, 0))

    def test_duration_must_be_positive(self):
        timeslot = TimeSlot(
            time=aware_dt(2026, 1, 27, 14, 0),
            duration_minutes=0,
            topic='Invalid Duration',
            contact=self.contact,
        )

        with self.assertRaises(ValidationError):
            timeslot.full_clean()

    def test_overlapping_timeslots_are_rejected(self):
        TimeSlot.objects.create(
            time=aware_dt(2026, 1, 27, 10, 0),
            duration_minutes=60,
            topic='First',
            contact=self.contact,
        )

        overlapping = TimeSlot(
            time=aware_dt(2026, 1, 27, 10, 30),
            duration_minutes=30,
            topic='Overlap',
            contact=self.contact,
        )

        with self.assertRaises(ValidationError):
            overlapping.full_clean()

    def test_adjacent_timeslots_are_allowed(self):
        TimeSlot.objects.create(
            time=aware_dt(2026, 1, 27, 10, 0),
            duration_minutes=60,
            topic='First',
            contact=self.contact,
        )

        adjacent = TimeSlot(
            time=aware_dt(2026, 1, 27, 11, 0),
            duration_minutes=30,
            topic='Adjacent',
            contact=self.contact,
        )
        adjacent.full_clean()
        adjacent.save()

        self.assertEqual(TimeSlot.objects.count(), 2)

    def test_valid_timeslot_without_contact_via_api(self):
        data = {
            'topic': 'Solo Meeting',
            'datetime': '2026-01-27T14:00:00',
            'contact': None,
        }
        client = APIClient()
        response = client.post('/api/timeslots', data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['contact'])


class TimeSlotKafkaProducerSignalTests(TestCase):
    def setUp(self):
        self.contact = Contact.objects.create(
            first_name='Kafka',
            last_name='Tester',
            email='kafka.tester@example.com',
            phone_number='+15555555555',
        )

    def test_timeslot_create_publishes_event_when_enabled(self):
        publisher = mock.Mock(return_value={'topic': 'appointments.created', 'partition': 0, 'offset': 3})

        with (
            override_settings(KAFKA_PRODUCER_ENABLED=True),
            mock.patch('calendar_api.services.appointment_events._import_publish_function', return_value=publisher),
            self.captureOnCommitCallbacks(execute=True),
        ):
            timeslot = TimeSlot.objects.create(
                time=aware_dt(2026, 1, 27, 16, 0),
                topic='Kafka Enabled',
                contact=self.contact,
            )

        publisher.assert_called_once()
        payload = publisher.call_args.args[0]
        self.assertEqual(payload['event_type'], 'appointments.created')
        self.assertEqual(payload['appointment']['appointment_id'], f'timeslot-{timeslot.id}')
        self.assertEqual(payload['appointment']['email'], self.contact.email)
        self.assertEqual(payload['notify']['email'], True)

    def test_timeslot_create_does_not_publish_when_disabled(self):
        with (
            override_settings(KAFKA_PRODUCER_ENABLED=False),
            mock.patch('calendar_api.services.appointment_events._import_publish_function') as import_mock,
            self.captureOnCommitCallbacks(execute=True),
        ):
            TimeSlot.objects.create(
                time=aware_dt(2026, 1, 27, 17, 0),
                topic='Kafka Disabled',
                contact=self.contact,
            )

        import_mock.assert_not_called()

    def test_timeslot_create_without_contact_skips_publisher(self):
        with (
            override_settings(KAFKA_PRODUCER_ENABLED=True),
            mock.patch('calendar_api.services.appointment_events._import_publish_function') as import_mock,
            self.captureOnCommitCallbacks(execute=True),
        ):
            TimeSlot.objects.create(
                time=aware_dt(2026, 1, 27, 18, 0),
                topic='No Contact',
                contact=None,
            )

        import_mock.assert_not_called()


class TimeSlotApiTests(APITestCase):
    def setUp(self):
        self.contact = Contact.objects.create(
            first_name='Jane',
            last_name='Smith',
            email='jane@example.com',
        )

    def create_internal_timeslot(self, *, topic, dt_str, duration_minutes=None, contact_id=None):
        payload = {
            'topic': topic,
            'datetime': dt_str,
            'contact': contact_id,
        }
        if duration_minutes is not None:
            payload['duration_minutes'] = duration_minutes
        return self.client.post('/api/timeslots', payload, format='json')

    def create_public_booking(self, *, email, dt_str, duration_minutes=None):
        timeslot = {
            'topic': 'Public Booking',
            'datetime': dt_str,
        }
        if duration_minutes is not None:
            timeslot['duration_minutes'] = duration_minutes

        payload = {
            'contact': {
                'firstName': 'Public',
                'lastName': 'User',
                'email': email,
                'phone': '1234567890',
                'timezone': 'America/Los_Angeles',
            },
            'timeslot': timeslot,
        }
        return self.client.post('/api/timeslots', payload, format='json')

    def test_create_timeslot_with_contact_id(self):
        response = self.create_internal_timeslot(
            topic='Meeting with Contact',
            dt_str='2026-01-27T15:00:00',
            contact_id=self.contact.id,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['contact'], self.contact.id)
        self.assertEqual(response.data['duration_minutes'], 30)

    def test_internal_create_supports_arbitrary_duration(self):
        response = self.create_internal_timeslot(
            topic='One-hour Internal Meeting',
            dt_str='2026-01-27T08:15:00',
            duration_minutes=60,
            contact_id=None,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['duration_minutes'], 60)

    def test_public_create_defaults_to_30_minutes(self):
        response = self.create_public_booking(
            email='public-default@example.com',
            dt_str='2026-01-27T10:00:00',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['timeslot']['duration_minutes'], 30)

    def test_public_create_rejects_non_30_minutes(self):
        response = self.create_public_booking(
            email='public-duration@example.com',
            dt_str='2026-01-27T10:00:00',
            duration_minutes=45,
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('30 minutes', response.data['error'])

    def test_public_create_rejects_before_public_window(self):
        response = self.create_public_booking(
            email='public-early@example.com',
            dt_str='2026-01-27T09:00:00',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('10:00 AM', response.data['error'])

    def test_public_create_rejects_non_half_hour_boundary(self):
        response = self.create_public_booking(
            email='public-quarter@example.com',
            dt_str='2026-01-27T10:15:00',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('30-minute boundary', response.data['error'])

    def test_overlap_is_rejected(self):
        first = self.create_internal_timeslot(
            topic='First',
            dt_str='2026-01-27T10:00:00',
            duration_minutes=60,
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        overlapping = self.create_internal_timeslot(
            topic='Overlap',
            dt_str='2026-01-27T10:30:00',
            duration_minutes=30,
        )
        self.assertEqual(overlapping.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('overlaps', str(overlapping.data).lower())

    def test_adjacent_slots_are_allowed(self):
        first = self.create_internal_timeslot(
            topic='First',
            dt_str='2026-01-27T10:00:00',
            duration_minutes=60,
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        adjacent = self.create_internal_timeslot(
            topic='Adjacent',
            dt_str='2026-01-27T11:00:00',
            duration_minutes=30,
        )
        self.assertEqual(adjacent.status_code, status.HTTP_201_CREATED)

    def test_timeslot_response_includes_end_time(self):
        response = self.create_internal_timeslot(
            topic='Meeting',
            dt_str='2026-01-27T14:00:00',
            duration_minutes=45,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('end_time', response.data)
        self.assertIsNotNone(response.data['end_time'])

    def test_list_timeslots(self):
        self.create_internal_timeslot(topic='First Meeting', dt_str='2026-01-27T10:00:00')
        self.create_internal_timeslot(topic='Second Meeting', dt_str='2026-01-27T14:00:00')

        response = self.client.get('/api/timeslots', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)

    def test_retrieve_single_timeslot(self):
        create = self.create_internal_timeslot(topic='Single Meeting', dt_str='2026-01-27T14:00:00')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)

        timeslot_id = create.data['id']
        response = self.client.get(f'/api/timeslots/{timeslot_id}', format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['topic'], 'Single Meeting')

    def test_update_timeslot(self):
        create = self.create_internal_timeslot(topic='Original Topic', dt_str='2026-01-27T14:00:00')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)

        timeslot_id = create.data['id']
        payload = {
            'topic': 'Updated Topic',
            'datetime': '2026-01-27T15:00:00',
            'duration_minutes': 90,
            'contact': None,
        }
        response = self.client.put(f'/api/timeslots/{timeslot_id}', payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['topic'], 'Updated Topic')
        self.assertEqual(response.data['duration_minutes'], 90)

    def test_delete_timeslot(self):
        create = self.create_internal_timeslot(topic='To Delete', dt_str='2026-01-27T14:00:00')
        self.assertEqual(create.status_code, status.HTTP_201_CREATED)

        timeslot_id = create.data['id']
        response = self.client.delete(f'/api/timeslots/{timeslot_id}', format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TimeSlot.objects.filter(id=timeslot_id).exists())

    def test_timeslot_requires_datetime(self):
        data = {
            'topic': 'Incomplete',
            'contact': None,
        }
        response = self.client.post('/api/timeslots', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('datetime', response.data)

    def test_by_day_endpoint_retrieves_timeslot(self):
        create_response = self.create_internal_timeslot(
            topic='Test Meeting',
            dt_str='2026-01-27T14:00:00',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        created_id = create_response.data['id']

        response = self.client.get('/api/timeslots/by-day?date=2026-01-27', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertGreater(len(response.data), 0)

        timeslot_ids = [ts['id'] for ts in response.data]
        self.assertIn(created_id, timeslot_ids)

    def test_by_day_endpoint_filters_by_date(self):
        response1 = self.create_internal_timeslot(
            topic='Meeting on Jan 27',
            dt_str='2026-01-27T14:00:00',
        )
        id_jan27 = response1.data['id']

        response2 = self.create_internal_timeslot(
            topic='Meeting on Jan 28',
            dt_str='2026-01-28T15:00:00',
        )
        id_jan28 = response2.data['id']

        response = self.client.get('/api/timeslots/by-day?date=2026-01-27', format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        timeslot_ids = [ts['id'] for ts in response.data]

        self.assertIn(id_jan27, timeslot_ids)
        self.assertNotIn(id_jan28, timeslot_ids)

    def test_by_day_endpoint_requires_date_parameter(self):
        response = self.client.get('/api/timeslots/by-day', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_by_day_endpoint_validates_date_format(self):
        response = self.client.get('/api/timeslots/by-day?date=01-27-2026', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

        response = self.client.get('/api/timeslots/by-day?date=2026-13-01', format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
