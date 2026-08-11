# Configuration

Configuration of `django-email-relay` is done through the `DJANGO_EMAIL_RELAY` dictionary in your Django settings.

Depending on whether you are configuring the relay service or the Django app, different settings are available. Some settings are available for both, while others are only available for one or the other. If you configure a setting that does not apply, for instance, if you configure something related to the relay service from one of the distributed Django apps, it will have no effect. See the individual sections for each setting below for more information.

All settings are optional. Here is an example configuration with the default values shown:

```python
DJANGO_EMAIL_RELAY = {
    "DATABASE_ALIAS": email_relay.conf.EMAIL_RELAY_DATABASE_ALIAS,  # "email_relay_db"
    "EMAIL_MAX_BATCH": None,
    "EMAIL_MAX_DEFERRED": None,
    "EMAIL_MAX_RETRIES": None,
    "EMPTY_QUEUE_SLEEP": 30,
    "EMAIL_THROTTLE": 0,
    "MESSAGES_BATCH_SIZE": None,
    "MESSAGES_RETENTION_SECONDS": None,
    "RELAY_HEALTHCHECK_METHOD": "GET",
    "RELAY_HEALTHCHECK_STATUS_CODE": 200,
    "RELAY_HEALTHCHECK_TIMEOUT": 5.0,
    "RELAY_HEALTHCHECK_URL": None,
}
```

```{toctree}
:hidden:

relay-service
```

## `DATABASE_ALIAS`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | Yes ✅       |
```

The database alias to use for the email relay database. This must match the database alias used in your `DATABASES` setting. A default is provided at `email_relay.conf.EMAIL_RELAY_DATABASE_ALIAS`. You should only need to set this if you are using a different database alias.

## `EMAIL_MAX_BATCH`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The maximum number of emails to send in a single batch. The default is `None`, which means there is no limit.

## `EMAIL_MAX_DEFERRED`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The maximum number of emails that can be deferred before the relay service stops sending emails. The default is `None`, which means there is no limit.

## `EMAIL_MAX_RETRIES`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The maximum number of times an email can be deferred before being marked as failed. The default is `None`, which means there is no limit.

## `EMPTY_QUEUE_SLEEP`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The time in seconds to wait before checking the queue for new emails to send. The default is `30` seconds.

## `EMAIL_THROTTLE`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The time in seconds to sleep between sending emails to avoid potential rate limits or overloading your SMTP server. The default is `0` seconds.

## `MESSAGES_BATCH_SIZE`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | No  🚫       |
| Django App    | Yes ✅       |
```

The batch size to use when bulk creating `Messages` in the database. The default is `None`, which means Django's default batch size will be used.

## `MESSAGES_RETENTION_SECONDS`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The time in seconds to keep `Messages` in the database before deleting them. `None` means the messages will be kept indefinitely, `0` means no messages will be kept, and any other integer value will be the number of seconds to keep messages. The default is `None`.

## `RELAY_HEALTHCHECK_METHOD`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The HTTP method to use for the healthcheck endpoint. [`RELAY_HEALTHCHECK_URL`](#relay_healthcheck_url) must also be set for this to have any effect. The default is `"GET"`.

## `RELAY_HEALTHCHECK_STATUS_CODE`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The expected HTTP status code for the healthcheck endpoint. [`RELAY_HEALTHCHECK_URL`](#relay_healthcheck_url) must also be set for this to have any effect. The default is `200`.

## `RELAY_HEALTHCHECK_TIMEOUT`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The timeout in seconds for the healthcheck endpoint. [`RELAY_HEALTHCHECK_URL`](#relay_healthcheck_url) must also be set for this to have any effect. The default is `5.0` seconds.

## `RELAY_HEALTHCHECK_URL`

```{table}
:align: left

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |
```

The URL to ping after a loop of sending emails is complete. This can be used to integrate with a service like [Healthchecks.io](https://healthchecks.io/) or [UptimeRobot](https://uptimerobot.com/). The default is `None`, which means no healthcheck will be performed.
