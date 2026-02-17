# Portfolio Calendar API (Minimal API)

Stateless C# Minimal API that receives appointment requests from the frontend
and publishes `appointments.created` events to Kafka.

## Why C#?

I’m not an expert in C#, but this service is meant to demonstrate language-
agnostic fundamentals: clear contracts, explicit boundaries, reliable messaging,
and a thin HTTP surface for a single responsibility.

## Portfolio Stack Description

Canonical system-wide architecture decisions and rationale live in the
`portfolio-frontend` repo:

`../portfolio-frontend/docs/architecture/repository-structure.md`

## Boundary Submodules

This repo references shared boundaries as submodules:

- `infra/messaging` -> `portfolio-infra-messaging`
- `contracts/notifier` -> `portfolio-notifier-contracts`

## Endpoints

- `GET /healthz`
- `POST /api/appointments`

### POST /api/appointments (request)

Contact requirements depend on enabled channels:
- If `notify.email` is enabled, `contact.email` is required.
- If `notify.sms` is enabled, `contact.phone` is required and normalized to E164.
If a channel is enabled but the required contact detail is missing, the request
is accepted but that channel is disabled for the emitted event.
If `contact.phone` is provided, it must be a valid phone number.

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
- `KAFKA_NOTIFY_EMAIL_DEFAULT` (default: `true`)
- `KAFKA_NOTIFY_SMS_DEFAULT` (default: `false`)
- `CONTACT_DEFAULT_PHONE_REGION` (default: `US`)

## Local Development

Prereqs:
- .NET SDK 8.x (TargetFramework net8.0)

### Docker (recommended)

```bash
docker compose up --build
```

### Dotnet (if installed)

```bash
dotnet run
```

## Kafka Local Setup

Start Kafka from `notifier_service`:

```bash
cd ../notifier_service
docker compose up -d kafka kafka-init
```

Then enable publishing:

```bash
export KAFKA_PRODUCER_ENABLED=true
```
