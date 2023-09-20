# django-email-relay

[![PyPI](https://img.shields.io/pypi/v/django-email-relay)](https://pypi.org/project/django-email-relay/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/django-email-relay)
![Django Version](https://img.shields.io/badge/django-3.2%20%7C%204.0%20%7C%204.1%20%7C%204.2-%2344B78B?labelColor=%23092E20)
<!-- https://shields.io/badges -->
<!-- django-3.2 | 4.0 | 4.1 | 4.2-#44B78B-->
<!-- labelColor=%23092E20 -->

## Requirements

- Python 3.6, 3.7, 3.8, or 3.9
- Django 3.2, 4.0, 4.1, or 4.2
- PostgreSQL (for provided Docker image)

## Installation

### Relay Service

### Django App

1. Install the package from PyPI:

```shell
pip install django-email-relay
```

2. Add `email_relay` to your `INSTALLED_APPS` setting:

```python
INSTALLED_APPS = [
    ...
    'email_relay',
    ...
]
```

3. Add the `EmailRelayBackend` to your `EMAIL_BACKEND` setting:

```python
EMAIL_BACKEND = 'email_relay.backend.RelayDatabaseEmailBackend'
```

4. Add the email relay database to your `DATABASES` setting. A default database alias is provided at `email_relay.conf.EMAIL_RELAY_DB_ALIAS`:
```python
from email_relay.conf import EMAIL_RELAY_DB_ALIAS

DATABASES = {
  ...
  EMAIL_RELAY_DB_ALIAS: {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "email_relay_db",
    "USER": "email_relay_user",
    "PASSWORD": "email_relay_password",
    "HOST": "localhost",
    "PORT": "5432",
  },
  ...
}
```

If you would like to use a different database alias, you will also need to set the `EMAIL_RELAY_DB_ALIAS` setting within your `DJANGO_EMAIL_RELAY` settings:
```python
DATABASES = {
  ...
  "some_alias": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "email_relay_db",
    "USER": "email_relay_user",
    "PASSWORD": "email_relay_password",
    "HOST": "localhost",
    "PORT": "5432",
  },
  ...
}

DJANGO_EMAIL_RELAY = {
  ...
  "EMAIL_RELAY_DB_ALIAS": "some_alias",
  ...
}
```

4. Add the `EmailRelayDatabaseRouter` to your `DATABASE_ROUTERS` setting:

```python
DATABASE_ROUTERS = [
    ...
    'email_relay.db.EmailRelayDatabaseRouter',
    ...
]
```

## Usage

## Configuration

## Inspiration

This package is heavily inspired by the [`django-mailer`](https://github.com/pinax/django-mailer) package. `django-mailer` is licensed under the MIT license, which is also the license used for this package. The required copyright notice is included in the [`LICENSE`](LICENSE) file for this package.
