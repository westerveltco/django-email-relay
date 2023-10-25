# Configuring the Relay Service

At a minimum, you should configure the relay service's connection to the database and how it will connect to your SMTP server, which, depending on your SMTP server, can include any or all the following Django settings:

- `EMAIL_HOST`
- `EMAIL_PORT`
- `EMAIL_HOST_USER`
- `EMAIL_HOST_PASSWORD`

Additionally, the service can be configured using any setting available to Django by default, for example, if you want to set a default from email (`DEFAULT_FROM_EMAIL`) or a common subject prefix (`EMAIL_SUBJECT_PREFIX`).

Configuration of the relay service differs depending on whether you are using the provided Docker image or the management command within a Django project.

## Docker

When running the relay service using Docker, config values are set via environment variables. The names of the environment variables are the same as the Django settings, e.g., to set `DEBUG` to `True`, you would set `-e "DEBUG=True"` when running the container.

For settings that are dictionaries, a `__` is used to separate the keys, e.g., to set `DATABASES["default"]["CONN_MAX_AGE"]` to `600` or 10 minutes, you would set `-e "DATABASES__default__CONN_MAX_AGE=600"`.

For the database connection, [`dj-database-url`](https://github.com/jazzband/dj-database-url) is used to parse the `DATABASE_URL` environment variable, e.g., `-e "DATABASE_URL=postgres://email_relay_user:email_relay_password@localhost:5432/email_relay_db"`.

## Django

When running the relay service from a Django project, config values are read from the Django settings for that project.
