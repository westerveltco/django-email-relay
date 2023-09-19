# django-email-relay

## Installation

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

4. Add the `EMAIL_RELAY_DB_SETTINGS` to your `DATABASES` setting.

This can be done either using the `EMAIL_RELAY_DATABASE_SETTINGS` dictionary which gets the database URL from the environment variable `EMAIL_RELAY_DATABASE_URL` by default, or by using the `get_email_relay_database_settings` function to get the database settings from a custom environment variable.

```python
import os
from email_relay.db import EMAIL_RELAY_DB_SETTINGS
from email_relay.db import get_email_relay_database_settings

DATABASES = {
    ...
    **EMAIL_RELAY_DB_SETTINGS,
    # get_email_relay_database_settings(os.environ.get("EMAIL_RELAY_DATABASE_URL"))  <- this doesn't work with the service
    ...
}
```

Alternatively, you can manually configure the database settings like any other Django database. If you do this, you can either use 'email_relay_db' as the database alias or a custom one. If you choose a custom one you must also this custom alias to the `EMAIL_RELAY_DB_ALIAS` setting to your `settings.py` file.
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
