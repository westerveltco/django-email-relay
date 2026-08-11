# Installation

You should install and setup the relay service provided by `django-email-relay` first before installing and configuring the Django app on your distributed Django projects. In the setup for the relay service, the database will be created and migrations will be run, which will need to be done before the distributed Django apps can use the relay service to send emails.

```{toctree}
:hidden:

relay-service
django-app
```
## Requirements

- Python 3.10, 3.11, 3.12 or 3.13
- Django 5.2, 6.0 or 6.1
- PostgreSQL (for provided Docker image)
