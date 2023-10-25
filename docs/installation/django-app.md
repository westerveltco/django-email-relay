# Django App

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

See the documentation [here](../configuration/index.md) for general information about configuring `django-email-relay`.
