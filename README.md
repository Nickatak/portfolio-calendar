# Portfolio Calendar API

Stateless C# Minimal API that receives appointment requests and publishes
`appointments.created` events to Kafka.

Full stack instructions live in the parent stack repo: `../README.md`.

## Role In The System

- Receives booking requests from the frontend.
- Validates/normalizes contact info.
- Emits `appointments.created` events to Kafka for downstream consumers.
- Remains stateless (no DB persistence).

## Dependencies

- Frontend: `../portfolio-frontend`
- Notifications/Kafka: `../notifier_service`
- BFF consumer (downstream): `../portfolio-bff`

## Endpoints

- `GET /healthz`
- `POST /api/appointments`

### POST /api/appointments (request)

Behavior notes:
- `notify.email` is always emitted as `true` (owner notifications).
- `notify.sms` is always emitted as `false` (SMS disabled for now).
- At least one valid contact method is required.
- If `contact.phone` is the only contact method, it must be a valid phone number.
  Otherwise invalid phone input is ignored.
  `contact.email` is optional and included in the payload when provided.

```json
{
  "contact": {
    "firstName": "Nick",
    "lastName": "A",
    "email": "nick@example.com",
    "phone": "+15551234567",
    "timezone": "America/Los_Angeles"
  },
  "appointment": {
    "topic": "Intro Call",
    "start_time": "2026-02-20T10:00:00Z",
    "end_time": "2026-02-20T10:30:00Z"
  }
}
```

### Response (accepted)

```json
{
  "appointment_id": "timeslot-1708440000000",
  "event_id": "evt-550e8400-e29b-41d4-a716-446655440000",
  "kafka_enabled": true,
  "published": true
}
```

## Kafka Event Contract

Events follow the schemas in:

- `contracts/notifier/events/appointments.created.schema.json`
- `contracts/notifier/events/appointments.created.dlq.schema.json`

This API is stateless and does not persist appointments. The event stream is the
system of record; a dashboard/read model can be built from Kafka later.

## CORS / Domain Restriction

CORS is configured via `ALLOWED_ORIGINS` (comma-separated). This only restricts
browser-based calls; it is not a security boundary for server-to-server traffic.
If you need stronger protection, use auth tokens or mTLS.

## Environment Variables

- `CALENDAR_API_PORT` (default: `8002`)
- `ALLOWED_ORIGINS` (default: `http://localhost:3000`)
- `KAFKA_PRODUCER_ENABLED` (default: `false`)
- `KAFKA_BOOTSTRAP_SERVERS` (default: `localhost:9092`)
- `KAFKA_TOPIC_APPOINTMENTS_CREATED` (default: `appointments.created`)
- `KAFKA_NOTIFY_EMAIL_DEFAULT` (default: `true`, currently ignored)
- `KAFKA_NOTIFY_SMS_DEFAULT` (default: `false`, currently ignored)
- `CONTACT_DEFAULT_PHONE_REGION` (default: `US`)

## Local Development

Prereqs:
- .NET SDK 8.x (TargetFramework net8.0)

Run locally (no Docker):
```bash
dotnet run
```

Note: Kafka publishing is disabled by default. To publish events, set
`KAFKA_PRODUCER_ENABLED=true` and ensure Kafka is running.

## Docker Development

```bash
docker compose up --build
```

This container expects Kafka reachable on the `notifier_service_default`
network (e.g., `kafka:19092`).

## Ports

- Calendar API: `8002`
