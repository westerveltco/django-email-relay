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

### Benefits

- By utilizing an internal SMTP server for email dispatch, `django-email-relay` reduces the security risks associated with using external ESPs, aligning with stringent corporate security policies.
- The relay service is available as either a standalone Docker image or a Django management command, giving you the flexibility to choose the deployment method that suits your infrastructure.
- Emails are stored in the database as part of a transaction. If a transaction fails, the associated email records can be rolled back, ensuring data consistency and integrity.
- By using an internal SMTP server, you are less likely to have your emails marked as spam or filtered by company-specific policies, ensuring more reliable delivery, especially if your primary audience is internal employees.
- By utilizing an existing internal SMTP server, you can potentially reduce costs associated with third-party ESPs.

### Limitations

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

## License

`django-email-relay` is licensed under the MIT license. See the [`LICENSE`](LICENSE) file for more information.

## Inspiration

This package is heavily inspired by the [`django-mailer`](https://github.com/pinax/django-mailer) package. `django-mailer` is licensed under the MIT license, which is also the license used for this package. The required copyright notice is included in the [`LICENSE`](LICENSE) file for this package.
