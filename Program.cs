using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;
using Confluent.Kafka;
using Microsoft.AspNetCore.Hosting;
using PhoneNumbers;

var builder = WebApplication.CreateBuilder(args);

var calendarPort = Env.GetString("CALENDAR_API_PORT", "8002");
var aspnetUrls = Environment.GetEnvironmentVariable("ASPNETCORE_URLS");
if (string.IsNullOrWhiteSpace(aspnetUrls))
{
    builder.WebHost.UseUrls($"http://0.0.0.0:{calendarPort}");
}

var allowedOrigins = Env.GetCsv("ALLOWED_ORIGINS", new[] { "http://localhost:3000" });

builder.Services.AddCors(options =>
{
    options.AddPolicy("default", policy =>
    {
        if (allowedOrigins.Length == 1 && allowedOrigins[0] == "*")
        {
            policy.AllowAnyOrigin();
        }
        else
        {
            policy.WithOrigins(allowedOrigins);
        }

        policy.AllowAnyHeader();
        policy.AllowAnyMethod();
    });
});

builder.Services.ConfigureHttpJsonOptions(options =>
{
    options.SerializerOptions.PropertyNamingPolicy = null;
    options.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull;
});

builder.Services.AddSingleton(KafkaSettings.FromEnvironment());
builder.Services.AddSingleton<KafkaPublisher>();

var app = builder.Build();

app.UseCors("default");

app.MapGet("/healthz", () => Results.Ok(new { status = "ok" }));

app.MapPost("/api/appointments", async (
    AppointmentRequest request,
    KafkaPublisher publisher,
    KafkaSettings settings,
    ILogger<Program> logger,
    CancellationToken cancellationToken) =>
{
    var email = string.IsNullOrWhiteSpace(request.Contact?.Email)
        ? null
        : request.Contact.Email!.Trim();
    var defaultPhoneRegion = Env.GetString("CONTACT_DEFAULT_PHONE_REGION", "US");
    var phoneE164 = PhoneNormalizer.NormalizeE164(request.Contact?.Phone, defaultPhoneRegion);
    var notifySmsRequested = settings.NotifySmsDefault;
    var notifyEmail = true;
    var notifySms = false;

    var errors = AppointmentValidator.Validate(request, email, phoneE164, notifyEmail, notifySms);
    if (errors.Count > 0)
    {
        return Results.BadRequest(new { errors });
    }

    var now = DateTimeOffset.UtcNow;
    var appointmentIdValue = now.ToUnixTimeMilliseconds();
    var appointmentId = $"timeslot-{appointmentIdValue}";
    var userId = appointmentIdValue.ToString(CultureInfo.InvariantCulture);

    var startUtc = request.Appointment.StartTime.ToUniversalTime();
    var endUtc = request.Appointment.EndTime.ToUniversalTime();
    var durationMinutes = (int)Math.Round((endUtc - startUtc).TotalMinutes, MidpointRounding.AwayFromZero);

    var payload = new AppointmentEvent(
        EventId: $"evt-{Guid.NewGuid()}",
        EventType: "appointments.created",
        OccurredAt: now.ToString("O", CultureInfo.InvariantCulture),
        Notify: new NotifyPayload(notifyEmail, notifySms),
        Appointment: new AppointmentPayload(
            AppointmentId: appointmentId,
            UserId: userId,
            StartTime: startUtc.ToString("O", CultureInfo.InvariantCulture),
            EndTime: endUtc.ToString("O", CultureInfo.InvariantCulture),
            DurationMinutes: durationMinutes,
            Time: startUtc.ToString("O", CultureInfo.InvariantCulture),
            Email: email,
            PhoneE164: phoneE164
        )
    );

    var payloadJson = JsonSerializer.Serialize(payload, JsonSerializerOptionsCache.Options);

    var publishResult = await publisher.PublishAsync(payloadJson, cancellationToken);

    if (!publishResult.Published)
    {
        logger.LogWarning(
            "Kafka publish skipped or failed. enabled={Enabled} error={Error}",
            settings.Enabled,
            publishResult.Error
        );
    }

    return Results.Accepted("/api/appointments", new AppointmentAcceptedResponse(
        AppointmentId: appointmentId,
        EventId: payload.EventId,
        KafkaEnabled: settings.Enabled,
        Published: publishResult.Published
    ));
});

app.Run();

internal static class Env
{
    public static string? Get(string key) => Environment.GetEnvironmentVariable(key);

    public static bool GetBool(string key, bool defaultValue)
    {
        var value = Get(key);
        if (string.IsNullOrWhiteSpace(value))
        {
            return defaultValue;
        }

        return value.Trim().ToLowerInvariant() switch
        {
            "1" or "true" or "t" or "yes" or "y" or "on" => true,
            "0" or "false" or "f" or "no" or "n" or "off" => false,
            _ => defaultValue
        };
    }

    public static string GetString(string key, string defaultValue)
    {
        var value = Get(key);
        return string.IsNullOrWhiteSpace(value) ? defaultValue : value.Trim();
    }

    public static string[] GetCsv(string key, string[] defaultValue)
    {
        var value = Get(key);
        if (string.IsNullOrWhiteSpace(value))
        {
            return defaultValue;
        }

        return value.Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
    }
}

internal sealed record KafkaSettings(
    bool Enabled,
    string BootstrapServers,
    string TopicAppointmentsCreated,
    bool NotifyEmailDefault,
    bool NotifySmsDefault
)
{
    public static KafkaSettings FromEnvironment()
    {
        return new KafkaSettings(
            Enabled: Env.GetBool("KAFKA_PRODUCER_ENABLED", false),
            BootstrapServers: Env.GetString("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            TopicAppointmentsCreated: Env.GetString("KAFKA_TOPIC_APPOINTMENTS_CREATED", "appointments.created"),
            NotifyEmailDefault: Env.GetBool("KAFKA_NOTIFY_EMAIL_DEFAULT", true),
            NotifySmsDefault: Env.GetBool("KAFKA_NOTIFY_SMS_DEFAULT", false)
        );
    }
}

internal sealed class KafkaPublisher : IDisposable
{
    private readonly KafkaSettings _settings;
    private readonly ILogger<KafkaPublisher> _logger;
    private readonly IProducer<Null, string>? _producer;

    public KafkaPublisher(KafkaSettings settings, ILogger<KafkaPublisher> logger)
    {
        _settings = settings;
        _logger = logger;

        if (!_settings.Enabled)
        {
            return;
        }

        var config = new ProducerConfig
        {
            BootstrapServers = _settings.BootstrapServers,
            Acks = Acks.All
        };

        _producer = new ProducerBuilder<Null, string>(config).Build();
    }

    public async Task<KafkaPublishResult> PublishAsync(string payload, CancellationToken cancellationToken)
    {
        if (!_settings.Enabled)
        {
            return KafkaPublishResult.Disabled();
        }

        if (_producer is null)
        {
            return KafkaPublishResult.Failed("Kafka producer not initialized.");
        }

        try
        {
            var result = await _producer.ProduceAsync(
                _settings.TopicAppointmentsCreated,
                new Message<Null, string> { Value = payload },
                cancellationToken
            );

            return KafkaPublishResult.Success(result.Topic, result.Partition.Value, result.Offset.Value);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Kafka publish failed.");
            return KafkaPublishResult.Failed(ex.Message);
        }
    }

    public void Dispose()
    {
        _producer?.Flush(TimeSpan.FromSeconds(5));
        _producer?.Dispose();
    }
}

internal sealed record KafkaPublishResult(bool Published, string? Error, string? Topic, int? Partition, long? Offset)
{
    public static KafkaPublishResult Success(string topic, int partition, long offset) =>
        new(true, null, topic, partition, offset);

    public static KafkaPublishResult Failed(string error) =>
        new(false, error, null, null, null);

    public static KafkaPublishResult Disabled() =>
        new(false, "Kafka publishing disabled.", null, null, null);
}

internal static class AppointmentValidator
{
    public static List<string> Validate(
        AppointmentRequest request,
        string? email,
        string? phoneE164,
        bool notifyEmail,
        bool notifySms)
    {
        var errors = new List<string>();
        var hasEmail = email is not null;
        var hasPhone = phoneE164 is not null;
        var phoneProvided = !string.IsNullOrWhiteSpace(request.Contact?.Phone);

        if (request.Contact is null)
        {
            errors.Add("contact is required");
            return errors;
        }

        if (!hasEmail && !hasPhone)
        {
            if (phoneProvided)
            {
                errors.Add("contact.phone must be a valid phone number");
            }
            else
            {
                errors.Add("contact.email or contact.phone is required");
            }
        }

        if (notifySms && !hasPhone)
        {
            if (phoneProvided)
            {
                errors.Add("contact.phone must be a valid phone number when notify.sms is enabled");
            }
            else
            {
                errors.Add("contact.phone is required when notify.sms is enabled");
            }
        }

        if (request.Appointment is null)
        {
            errors.Add("appointment is required");
            return errors;
        }

        if (request.Appointment.EndTime <= request.Appointment.StartTime)
        {
            errors.Add("appointment.end_time must be after appointment.start_time");
        }

        return errors;
    }
}

internal static class PhoneNormalizer
{
    public static string? NormalizeE164(string? value, string? defaultRegion)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return null;
        }

        var trimmed = value.Trim();
        var region = string.IsNullOrWhiteSpace(defaultRegion)
            ? "US"
            : defaultRegion.Trim().ToUpperInvariant();

        try
        {
            var util = PhoneNumberUtil.GetInstance();
            var parsed = util.Parse(trimmed, region);
            if (!util.IsValidNumber(parsed))
            {
                return null;
            }

            return util.Format(parsed, PhoneNumberFormat.E164);
        }
        catch (NumberParseException)
        {
            return null;
        }
    }
}

internal static class JsonSerializerOptionsCache
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = null,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };
}

public sealed record AppointmentRequest(
    [property: JsonPropertyName("contact")] ContactPayload Contact,
    [property: JsonPropertyName("appointment")] AppointmentInput Appointment
);

public sealed record ContactPayload(
    [property: JsonPropertyName("firstName")] string? FirstName,
    [property: JsonPropertyName("lastName")] string? LastName,
    [property: JsonPropertyName("email")] string? Email,
    [property: JsonPropertyName("phone")] string? Phone,
    [property: JsonPropertyName("timezone")] string? Timezone
);

public sealed record AppointmentInput(
    [property: JsonPropertyName("topic")] string? Topic,
    [property: JsonPropertyName("start_time")] DateTimeOffset StartTime,
    [property: JsonPropertyName("end_time")] DateTimeOffset EndTime
);

public sealed record AppointmentEvent(
    [property: JsonPropertyName("event_id")] string EventId,
    [property: JsonPropertyName("event_type")] string EventType,
    [property: JsonPropertyName("occurred_at")] string OccurredAt,
    [property: JsonPropertyName("notify")] NotifyPayload Notify,
    [property: JsonPropertyName("appointment")] AppointmentPayload Appointment
);

public sealed record NotifyPayload(
    [property: JsonPropertyName("email")] bool Email,
    [property: JsonPropertyName("sms")] bool Sms
);

public sealed record AppointmentPayload(
    [property: JsonPropertyName("appointment_id")] string AppointmentId,
    [property: JsonPropertyName("user_id")] string UserId,
    [property: JsonPropertyName("start_time")] string StartTime,
    [property: JsonPropertyName("end_time")] string EndTime,
    [property: JsonPropertyName("duration_minutes")] int DurationMinutes,
    [property: JsonPropertyName("time")] string Time,
    [property: JsonPropertyName("email")] string? Email,
    [property: JsonPropertyName("phone_e164")] string? PhoneE164
);

public sealed record AppointmentAcceptedResponse(
    [property: JsonPropertyName("appointment_id")] string AppointmentId,
    [property: JsonPropertyName("event_id")] string EventId,
    [property: JsonPropertyName("kafka_enabled")] bool KafkaEnabled,
    [property: JsonPropertyName("published")] bool Published
);
