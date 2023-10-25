# Usage

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

```{toctree}
:hidden:

relay-healthcheck
```
