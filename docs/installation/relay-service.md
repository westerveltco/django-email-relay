# Relay Service

The relay service provided by `django-email-relay` is responsible for reading a central database queue and sending emails from that queue through an SMTP server. As such, it should be run on infrastructure that has access to the SMTP server you would like to use. There are currently two ways to run the service:

1. A Docker image
2. A `runrelay` management command to be run from within a Django project

If you are using the Docker image, only PostgreSQL is supported. However, when using the management command directly, you can use whatever database you are using with the Django project it is being run from, provided your other externally hosted Django projects that you would like to relay emails for also have access to the same database. If you would like the Docker image to support other databases, please [open an issue](https://github.com/westerveltco/django-email-relay/issues/new) and it will be considered.

Installation of the relay service differs depending on whether you are using the provided Docker image or the management command.

## Docker

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

See the documentation [here](../configuration/index.md) for general information about configuring `django-email-relay`, [here](../configuration/relay-service.md) for information about configuring the relay service, and [here](../configuration/relay-service.md#docker) for information specifically related to configuring the relay service as a Docker container.

## Django

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

See the documentation [here](../configuration/index.md) for general information about configuring `django-email-relay`, [here](../configuration/relay-service.md) for information about configuring the relay service, and [here](../configuration/relay-service.md#django) for information specifically related to configuring the relay service as a Django app.
