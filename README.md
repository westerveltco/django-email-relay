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
- As a way to combat phishing emails, we treat and process internal and external emails differently. This meant that in order for our applications' transactional emails to be treated as internal, adjustments and exceptions would need to be made, which our security team was not comfortable with.

We have an internal SMTP server that can be used for any application deployed on-premises, which bypasses most of these issues. However, it is not, and there are no plans to make it publicly accessible -- either through opening firewall ports or by using a service like Tailscale. This meant that we needed to find another way to route emails from our cloud-hosted Django applications to this internal SMTP server.

After discussing with our infrastructure and security team, we thought about what would be the simplest and most straightforward to develop and deploy while also not compromising on security. Taking inspiration from another Django package, [`django-mailer`](https://github.com/pinax/django-mailer/), we decided that a solution utilizing a central database queue that our cloud-hosted Django applications can use to store emails to be sent and a relay service that can be run on-premises that reads from that queue would fulfill those requirements. This is what `django-email-relay` is.

## Limitations

As `django-email-relay` is based on `django-mailer`, it shares a lot of the same limitations, detailed [here](https://github.com/pinax/django-mailer/blob/863a99752e6928f9825bae275f69bf8696b836cb/README.rst#limitations). Namely:

- Since file attachments are stored in a database, large attachments can potentially cause space and query issues.
- From the Django applications sending emails, it is not possible to know whether an email has been sent or not, only whether it has been successfully queued for sending.
- Emails are not sent immediately but instead saved in a database queue to be used by the relay service. This means that emails will not be sent unless the relay service is started and running.
- Due to the distributed nature of the package and the fact that there are database models, and thus potentially migrations to apply, care should be taken when upgrading to ensure that all Django projects using `django-email-relay` are upgraded at roughly the same time. See the [Updating](#updating) section of the documentation for more information.

## Requirements

- Python 3.8, 3.9, 3.10, 3.11, or 3.12
- Django 3.2, 4.1, or 4.2
- PostgreSQL (for provided Docker image)

## Installation

You should install and setup the relay service provided by `django-email-relay` first before installing and configuring the Django app on your distributed Django projects. In the setup for the relay service, the database will be created and migrations will be run, which will need to be done before the distributed Django apps can use the relay service to send emails.

### Relay Service

The relay service provided by `django-email-relay` is responsible for reading a central database queue and sending emails from that queue through an SMTP server. As such, it should be run on infrastructure that has access to the SMTP server you would like to use. There are currently two ways to run the service:

1. A Docker image
2. A `runrelay` management command to be run from within a Django project

If you are using the Docker image, only PostgreSQL is supported. However, when using the management command directly, you can use whatever database you are using with the Django project it is being run from, provided your other externally hosted Django projects that you would like to relay emails for also have access to the same database. If you would like the Docker image to support other databases, please [open an issue](https://github.com/westerveltco/django-email-relay/issues/new) and it will be considered.

Installation of the relay service differs depending on whether you are using the provided Docker image or the management command.

#### Docker

A prebuilt Docker image is provided via the GitHub Container Registry, located here:

```
ghcr.io/westerveltco/django-email-relay
```

It can be run any way you would normally run a Docker container, for instance, through the CLI:

```shell
docker run -d \
  -e "DATABASE_URL=postgres://email_relay_user:email_relay_password@localhost:5432/email_relay_db" \
  -e "EMAIL_HOST=smtp.example.com" \
  -e "EMAIL_PORT=25" \
  --restart unless-stopped \
  ghcr.io/westerveltco/django-email-relay:latest
```

It is recommended to pin to a specific version, though if you prefer, you can ride the lightning by always pulling the `latest` image.

The `migrate` step is baked into the image, so there is no need to run it yourself.

See the documentation [here](#configuration) for general information about configuring `django-email-relay`, [here](#relay-service-1) for information about configuring the relay service, and [here](#docker-1) for information specifically related to configuring the relay service as a Docker container.

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

3. Run the `migrate` management command to create the email relay database:

```shell
python manage.py migrate
```

4. Run the `runrelay` management command to start the relay service. This can be done in many different ways, for instance, via a task runner, such as Celery or Django-Q2, or using [supervisord](https://supervisord.org/) or systemd service unit file.

```shell
python manage.py runrelay
```

See the documentation [here](#configuration) for general information about configuring `django-email-relay`, [here](#relay-service-1) for information about configuring the relay service, and [here](#django-1) for information specifically related to configuring the relay service as a Django app.

### Django App

For each distributed Django project that you would like to use the preferred SMTP server, you will need to install the `django-email-relay` package and do some basic configuration.

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

As `django-email-relay` involves database models and the potential for migrations, care should be taken when updating to ensure that all Django projects using `django-email-relay` are upgraded at roughly the same time. See the [deprecation policy](#deprecation-policy) for more information regarding backward incompatible changes.

When updating to a new version, it is recommended to follow the following steps:

1. Update the relay service to the new version. As part of the update process, the relay service should run any migrations that are needed. If using the provided Docker container, this is done automatically as Django's `migrate` command is baked into the image. When running the relay service from a Django project, you will need to run the `migrate` command yourself, either as part of your deployment strategy or manually.
2. Update all distributed projects to the new version.

### Deprecation Policy

Any changes that involve models and/or migrations, or anything else that is potentially backward incompatible, will be split across two or more releases:

1. A release that adds the changes in a backward compatible way, with a deprecation warning. This release will be tagged with a minor version bump, e.g., `0.1.0` to `0.2.0`.
2. A release that removes the backward compatible changes and removes the deprecation warning. This release will be tagged with a major version bump, e.g., `0.2.0` to `1.0.0`.

This is unlikely to happen often, but it is important to keep in mind when updating.

A major release does not necessarily mean that there are breaking changes or ones involving models and migrations. You should always check the [changelog](CHANGELOG.md) and a version's release notes for more information.

## Usage

Once your Django project is configured to use `email_relay.backend.RelayDatabaseEmailBackend` as its `EMAIL_BACKEND`, sending email is as simple as using Django's built-in ways of sending email, such as the `send_mail` method:

```python
from django.core.mail import send_mail

send_mail(
    "Subject here",
    "Here is the message.",
    "from@example.com",
    ["to@example.com"],
    fail_silently=False,
)
```

Any emails sent this way, or one of the other ways Django provides, will be stored in the database queue and sent by the relay service.

See the Django documentation on [sending email](https://docs.djangoproject.com/en/dev/topics/email/) for more information.

### Relay Service Health Check

As mentioned in [limitations](#limitations) above, if the relay service is not running, or otherwise not operational, emails will not be sent out. To help with this, `django-email-relay` provides a way to send a health check ping to a URL of your choosing after each loop of sending emails is complete. This can be used to integrate with a service like [Healthchecks.io](https://healthchecks.io/) or [UptimeRobot](https://uptimerobot.com/).

To get started, you will need to install the package with the `hc` extra. If you are using the included Docker image, this is done automatically. If you are using the management command directly from a Django project, you will need to adjust your installation command:

```shell
pip install django-email-relay[hc]
```

At a minimum, you will need to configure which URL to ping after a loop of sending emails is complete. This can be done by setting the [`RELAY_HEALTHCHECK_URL`](#relay_healthcheck_url) setting in your `DJANGO_EMAIL_RELAY` settings:

```python
DJANGO_EMAIL_RELAY = {
    "RELAY_HEALTHCHECK_URL": "https://example.com/healthcheck",
}
```

It should be set to the URL provided by your health check service. If available, you should set the schedule of the health check within the service to what you have configured for the relay service's [`EMPTY_QUEUE_SLEEP`](#empty_queue_sleep) setting, which is `30` seconds by default.

There are also a few other settings that can be configured, such as the HTTP method to use, the expected HTTP status code, and the timeout. See the [configuration](#configuration) section for more information.

## Configuration

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

The time in seconds to sleep between sending emails to avoid potential rate limits or overloading your SMTP server. The default is `0` seconds.

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

#### `RELAY_HEALTHCHECK_METHOD`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The HTTP method to use for the healthcheck endpoint. [`RELAY_HEALTHCHECK_URL`](#relay_healthcheck_url) must also be set for this to have any effect. The default is `"GET"`.

#### `RELAY_HEALTHCHECK_STATUS_CODE`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The expected HTTP status code for the healthcheck endpoint. [`RELAY_HEALTHCHECK_URL`](#relay_healthcheck_url) must also be set for this to have any effect. The default is `200`.

#### `RELAY_HEALTHCHECK_TIMEOUT`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The timeout in seconds for the healthcheck endpoint. [`RELAY_HEALTHCHECK_URL`](#relay_healthcheck_url) must also be set for this to have any effect. The default is `5.0` seconds.

#### `RELAY_HEALTHCHECK_URL`

| Component     | Configurable |
|---------------|--------------|
| Relay Service | Yes ✅       |
| Django App    | No 🚫        |

The URL to ping after a loop of sending emails is complete. This can be used to integrate with a service like [Healthchecks.io](https://healthchecks.io/) or [UptimeRobot](https://uptimerobot.com/). The default is `None`, which means no healthcheck will be performed.

### Relay Service

At a minimum, you should configure how the relay service will connect to your SMTP server, which, depending on your SMTP server, can include any or all the following Django settings:

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

Additionally, the service can be configured using any setting available to Django by default, for example, if you want to set a default from email (`DEFAULT_FROM_EMAIL`) or a common subject prefix (`EMAIL_SUBJECT_PREFIX`).

Configuration of the relay service differs depending on whether you are using the provided Docker image or the management command within a Django project.

#### Docker

When running the relay service using Docker, config values are set via environment variables. The names of the environment variables are the same as the Django settings, e.g., to set `DEBUG` to `True`, you would set `-e "DEBUG=True"` when running the container.

For settings that are dictionaries, a `__` is used to separate the keys, e.g., to set `DATABASES["default"]["CONN_MAX_AGE"]` to `600` or 10 minutes, you would set `-e "DATABASES__default__CONN_MAX_AGE=600"`.

#### Django

When running the relay service from a Django project, config values are read from the Django settings for that project.

## Contributing

All contributions are welcome! Besides code contributions, this includes things like documentation improvements, bug reports, and feature requests.

You should first check if there is a [GitHub issue](https://github.com/westerveltco/django-email-relay/issues) already open or related to what you would like to contribute. If there is, please comment on that issue to let others know you are working on it. If there is not, please open a new issue to discuss your contribution.

Not all contributions need to start with an issue, such as typo fixes in documentation or version bumps to Python or Django that require no internal code changes, but generally, it is a good idea to open an issue first.

We adhere to Django's Code of Conduct in all interactions and expect all contributors to do the same. Please read the [Code of Conduct](https://www.djangoproject.com/conduct/) before contributing.

### Setup

The following setup steps assume you are using a Unix-like operating system, such as Linux or macOS, and that you have a [supported](#requirements) version of Python installed. If you are using Windows, you will need to adjust the commands accordingly. If you do not have Python installed, you can visit [python.org](https://www.python.org/) for instructions on how to install it for your operating system.

1. Fork the repository and clone it locally.
2. Create a virtual environment and activate it. You can use whatever tool you prefer for this. Below is an example using the Python standard library's `venv` module:

```shell
python -m venv venv
source venv/bin/activate
```

3. Install `django-email-relay` and the `dev` dependencies in editable mode:

```shell
python -m pip install -e '.[dev]'
```

### Testing

We use [`pytest`](https://docs.pytest.org/) for testing and [`nox`](https://nox.thea.codes/) to run the tests in multiple environments.

To run the test suite against the current environment, run:

```shell
python -m pytest
```

To run the test suite against all supported versions of Python and Django, run:

```shell
python -m nox
```

### `just`

[`just`](https://github.com/casey/just) is a command runner that is used to run common commands, similar to `make` or `invoke`. A `Justfile` is provided at the base of the repository, which contains commands for common development tasks, such as running the test suite or linting.

To see a list of all available commands, ensure `just` is installed and run the following command at the base of the repository:

```shell
just
````

## License

`django-email-relay` is licensed under the MIT license. See the [`LICENSE`](LICENSE) file for more information.

## Inspiration

This package is heavily inspired by the [`django-mailer`](https://github.com/pinax/django-mailer) package. `django-mailer` is licensed under the MIT license, which is also the license used for this package. The required copyright notice is included in the [`LICENSE`](LICENSE) file for this package.
