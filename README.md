# Calendar API

Django + DRF backend for scheduling contact calls used by the portfolio site.

## Current Scope

- Time slot CRUD via `/api/timeslots`
- Day filter endpoint via `/api/timeslots/by-day?date=YYYY-MM-DD`
- Optional contact creation on booking
- Custom Django admin at `/admin/`
- Health endpoint at `/healthz`

## Quickstart (Local)

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Create env file:
   ```bash
   cp .env.example .env
   ```
3. Install dependencies and migrate:
   ```bash
   make setup
   ```
4. Run the API:
   ```bash
   make runserver
   ```

The API runs on `http://localhost:8000`.

## Environment Variables

See `.env.example` for defaults.

- `SECRET_KEY`
- `DEBUG`
- `ALLOWED_HOSTS` (comma-separated)
- `TIME_ZONE`
- `CORS_ALLOWED_ORIGINS` (comma-separated)
- `CSRF_TRUSTED_ORIGINS` (comma-separated)
- `KAFKA_PRODUCER_ENABLED`
- `KAFKA_NOTIFY_EMAIL_DEFAULT`
- `KAFKA_NOTIFY_SMS_DEFAULT`
- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_TOPIC_APPOINTMENTS_CREATED`
- `KAFKA_TOPIC_APPOINTMENTS_CREATED_DLQ`

## Kafka Producer Integration

`calendar_api` publishes `appointments.created` events when a new `TimeSlot` is created and:
- `KAFKA_PRODUCER_ENABLED=true`
- the timeslot has a contact with a non-empty email

Publishing uses `kafka-notifications-lib` (`notifier_microservice`) and sends
payloads shaped for the notifier worker.

Default behavior is safe for local development: producer is disabled until
explicitly enabled.

Contract schemas for these payloads are tracked at:
- `contracts/notifier/events/appointments.created.schema.json` (producer contract)
- `contracts/notifier/events/appointments.created.dlq.schema.json` (DLQ envelope)

## API Endpoints

- `GET /healthz` - service health check
- `GET /api/timeslots` - list slots (supports `?is_active=true|false`)
- `POST /api/timeslots` - create slot
- `GET /api/timeslots/{id}` - get one slot
- `PUT /api/timeslots/{id}` - update slot
- `DELETE /api/timeslots/{id}` - delete slot
- `GET /api/timeslots/by-day?date=YYYY-MM-DD` - list slots for one date

Notes:
- Router uses `trailing_slash=False`, so endpoints are defined without trailing `/`.
- `duration_minutes` defaults to `30` and can be set for internal/admin use.
- Public bookings (nested `contact` + `timeslot` payload) enforce 30-minute slots between 10:00 and 17:30.

### Example Booking Payload (contact + timeslot)

```json
{
  "contact": {
    "firstName": "Nick",
    "lastName": "A",
    "email": "nick@example.com",
    "phone": "1234567890",
    "timezone": "America/Los_Angeles"
  },
  "timeslot": {
    "topic": "Intro Call",
    "start_time": "2026-02-20T10:00:00Z",
    "end_time": "2026-02-20T10:45:00Z"
  }
}
```

## Useful Commands

```bash
make help
make check
make test
make shell
make clean
```

## Docker

Build and run directly from this repo:

```bash
make docker-build
make docker-run
```

Or run as part of this monorepo from the root using Docker Compose.
