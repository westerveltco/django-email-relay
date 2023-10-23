# django-email-relay

[![PyPI](https://img.shields.io/pypi/v/django-email-relay)](https://pypi.org/project/django-email-relay/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-email-relay)
![Django Version](https://img.shields.io/badge/django-3.2%20%7C%204.1%20%7C%204.2-%2344B78B?labelColor=%23092E20)
<!-- https://shields.io/badges -->
<!-- django-3.2 | 4.1 | 4.2-#44B78B -->
<!-- labelColor=%23092E20 -->

`django-email-relay` enables Django projects without direct access to a preferred SMTP server to use that server for email dispatch.

It consists of two parts:

1. A Django app with a custom email backend that stores emails in a central database queue. This is what you will use on all the distributed Django projects that you would like to give access to the preferred SMTP server.

2. A relay service that reads from this queue to orchestrate email sending. It is available as either a standalone Docker image or a management command to be used within a Django project that does have access to the preferred SMTP server.

## Why?

At [The Westervelt Company](https://github.com/westerveltco), we primarily host our Django applications in the cloud. The majority of the emails we send are to internal Westervelt employees. Prior to developing and using `django-email-relay`, we were using an external Email Service Provider (ESP) to send these emails. This worked well enough, but we ran into a few issues:

- Emails sent by our applications had a tendency to sometimes be marked as spam or otherwise filtered by our company's email provider, which makes using an ESP essentially pointless.
- As a way to combat phishing emails, we treat and process internal and external emails differently. This meant that in order for our applications' transactional emails to be treated as internal, adjustments and exceptions would need to be made which our security team was not comfortable with.

We have an internal SMTP server that can be used for any application deployed on premises which bypasses most of these issues. However, it is not, and there are no plans to make it, publicly accessible -- either through opening firewall ports or by using a service like Tailscale. This meant that we needed to find another way to route emails from our cloud hosted Django applications to this internal SMTP server.

After discussing with our infrastructure and security team, we thought about what would be the simplest and most straightforward to develop and deploy while also not compromising on security. Taking inspiration from another Django package, [`django-mailer`](https://github.com/pinax/django-mailer/), we decided that a solution utilizing a central database queue that our cloud hosted Django applications can use to store emails to be sent and a relay service that can be run on premises that reads from that queue would fulfill those requirements. This is what `django-email-relay` is.

## Requirements

- Python 3.8, 3.9, 3.10, 3.11, or 3.12
- Django 3.2, 4.1, or 4.2
- PostgreSQL (for provided Docker image)

## Installation

### Relay Service

The relay service provided by `django-email-relay` is responsible for reading a central database queue and sending emails from that queue through an SMTP server. As such, it should be run on infrastructure that has access to the SMTP server you would like to use. There currently two ways to run the service:

1. A Docker image
2. A `runrelay` management command to be run from within a Django project

If you are using the Docker image, only PostgreSQL is supported. However, when using the management command directly you can use whatever database you are using with the Django project it is being run from, provided your other externally hosted Django projects that you would like to relay emails for also have access to the same database. If you would like the Docker image to support other databases, please [open an issue](https://github.com/westerveltco/django-email-relay/issues/new) and it will be considered.

Installation of the relay service differs depending on whether you are using the provided Docker image or the management command.

#### Docker

A prebuilt Docker image is provided via the GitHub Container Registry, located here:

```
ghcr.io/westerveltco/django-email-relay
```

It can be run anyway you would normally run a Docker container, for instance through the CLI:

```shell
docker run -d \
  -e "EMAIL_HOST=smtp.example.com" \
  -e "EMAIL_PORT=25" \
  --restart unless-stopped \
  ghcr.io/westerveltco/django-email-relay:latest
```

It is recommended to pin to a specific version, though if you prefer you can ride the lightning by always pulling the `latest` image.

See the documentation [here](#configuration) for general information about configuring `django-email-relay`, [here](#relay-service-1) for general information about configuring the relay service, and [here](#docker-1) for information specifically related to configuring the relay service as a Docker container.

#### Django

If you have a Django project already deployed that has access to the preferred SMTP server, you can skip using the Docker image and install the package and use the included `runrelay` management method instead.

1. Install the package from PyPI:

```shell
pip install django-email-relay
```

2. Add `email_relay` to your `INSTALLED_APPS` setting:

```python
INSTALLED_APPS = [
    # ...
    "email_relay",
    # ...
]
```

3. Run the `runrelay` management command to start the relay service. This can be done many different ways, for instance via a task runner, such as Celery or Django-Q2, or using [supervisord](https://supervisord.org/) or systemd service unit file.

```shell
python manage.py runrelay
```

See the documentation [here](#configuration) for general information about configuring `django-email-relay`, [here](#relay-service-1) for general information about configuring the relay service, and [here](#django-1) for information specifically related to configuring the relay service as a Django app.

### Django App

1. Install the package from PyPI:

```shell
pip install django-email-relay
```

2. Add `email_relay` to your `INSTALLED_APPS` setting:

```python
INSTALLED_APPS = [
    # ...
    "email_relay",
    # ...
]
```

3. Add the `RelayDatabaseEmailBackend` to your `EMAIL_BACKEND` setting:

```python
EMAIL_BACKEND = "email_relay.backend.RelayDatabaseEmailBackend"
```

4. Add the email relay database to your `DATABASES` setting. A default database alias is provided at `email_relay.conf.EMAIL_RELAY_DATABASE_ALIAS` which you can import and use:

```python
from email_relay.conf import EMAIL_RELAY_DATABASE_ALIAS

DATABASES = {
    # ...
    EMAIL_RELAY_DATABASE_ALIAS: {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "email_relay_db",
        "USER": "email_relay_user",
        "PASSWORD": "email_relay_password",
        "HOST": "localhost",
        "PORT": "5432",
    },
    # ...
}
```

If you would like to use a different database alias, you will also need to set the `DATABASE_ALIAS` setting within your `DJANGO_EMAIL_RELAY` settings:

```python
DATABASES = {
    # ...
    "some_alias": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "email_relay_db",
        "USER": "email_relay_user",
        "PASSWORD": "email_relay_password",
        "HOST": "localhost",
        "PORT": "5432",
    },
    # ...
}

DJANGO_EMAIL_RELAY = {
    # ...
    "DATABASE_ALIAS": "some_alias",
    # ...
}
```

4. Add the `EmailDatabaseRouter` to your `DATABASE_ROUTERS` setting:

```python
DATABASE_ROUTERS = [
    # ...
    "email_relay.db.EmailDatabaseRouter",
    # ...
]
```

See the documentation [here](#configuration) for general information about configuring `django-email-relay`.

## Updating

TODO

## Usage

TODO

## Configuration

Configuration of `django-email-relay` is done through the `DJANGO_EMAIL_RELAY` dictionary in your Django settings.

Depending on whether you are configuring the relay service or the Django app, different settings are available: some settings are available for both, while others are only available for one or the other. If you configure a setting that does not apply, for instance if you configure something related to the relay service from one of the distributed Django apps, it will have no effect. See the individual sections for each setting below for more information.

All settings are optional. Here is an example configuration, with the default values shown:

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
}
```

#### `DATABASE_ALIAS`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | Yes ✅       |

The database alias to use for the email relay database. This must match the database alias used in your `DATABASES` setting. A default is provided at `email_relay.conf.EMAIL_RELAY_DATABASE_ALIAS`. You should only need to set this if you are using a different database alias.

#### `EMAIL_MAX_BATCH`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The maximum number of emails to send in a single batch. The default is `None`, which means there is no limit.

#### `EMAIL_MAX_DEFERRED`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The maximum number of emails that can be deferred before the relay service stops sending emails. The default is `None`, which means there is no limit.

#### `EMAIL_MAX_RETRIES`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The maximum number of times an email can be deferred before being marked as failed. The default is `None`, which means there is no limit.

#### `EMPTY_QUEUE_SLEEP`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The time in seconds to wait before checking the queue for new emails to send. The default is `30` seconds.

#### `EMAIL_THROTTLE`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The time in seconds to sleep between sending emails, to avoid potential rate limits or overloading your SMTP server. The default is `0` seconds.

#### `MESSAGES_BATCH_SIZE`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | No  🚫       |
| Django App    | Yes ✅       |

The batch size to use when bulk creating `Messages` in the database. The default is `None`, which means Django's default batch size will be used.

#### `MESSAGES_RETENTION_SECONDS`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The time in seconds to keep `Messages` in the database before deleting them. `None` means the messages will be kept indefinitely, `0` means no messages will be kept, and any other integer value will be the number of seconds to keep messages. The default is `None`.

### Relay Service

At a minimum, you should configure how the relay service will connect to your SMTP server, which depending on your SMTP server can include any or all the following Django settings:

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

Additionally, the service can be configured using any setting available to Django by default, for example if you want to set a default from email (`DEFAULT_FROM_EMAIL`) or a common subject prefix (`EMAIL_SUBJECT_PREFIX`).

Configuration of the relay service differs depending on whether you are using the provided Docker image or the management command within a Django project.

#### Docker

When running the relay service using Docker, config values are set via environment variables. The names of the environment variables are the same as the Django settings, e.g. to set `DEBUG` to `True`, you would set `-e "DEBUG=True"` when running the container.

For settings that are dictionaries, a `__` is used to separate the keys, e.g. to set `DATABASES["default"]["CONN_MAX_AGE"]` to `600` or 10 minutes, you would set `-e "DATABASES__default__CONN_MAX_AGE=600"`.

#### Django

When running the relay service from a Django project, config values are read from the Django settings for that project.

## Contributing

TODO

## Inspiration

This package is heavily inspired by the [`django-mailer`](https://github.com/pinax/django-mailer) package. `django-mailer` is licensed under the MIT license, which is also the license used for this package. The required copyright notice is included in the [`LICENSE`](LICENSE) file for this package.
