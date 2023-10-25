# Relay Service Health Check

As mentioned in [limitations](../index.md#limitations), if the relay service is not running, or otherwise not operational, emails will not be sent out. To help with this, `django-email-relay` provides a way to send a health check ping to a URL of your choosing after each loop of sending emails is complete. This can be used to integrate with a service like [Healthchecks.io](https://healthchecks.io/) or [UptimeRobot](https://uptimerobot.com/).

To get started, you will need to install the package with the `hc` extra. If you are using the included Docker image, this is done automatically. If you are using the management command directly from a Django project, you will need to adjust your installation command:

```shell
pip install django-email-relay[hc]
```

At a minimum, you will need to configure which URL to ping after a loop of sending emails is complete. This can be done by setting the [`RELAY_HEALTHCHECK_URL`](../configuration/index.md#relay_healthcheck_url) setting in your `DJANGO_EMAIL_RELAY` settings:

```python
DJANGO_EMAIL_RELAY = {
    "RELAY_HEALTHCHECK_URL": "https://example.com/healthcheck",
}
```

It should be set to the URL provided by your health check service. If available, you should set the schedule of the health check within the service to what you have configured for the relay service's [`EMPTY_QUEUE_SLEEP`](../configuration/index.md#empty_queue_sleep) setting, which is `30` seconds by default.

There are also a few other settings that can be configured, such as the HTTP method to use, the expected HTTP status code, and the timeout. See the [configuration](../configuration/index.md) section for more information.
