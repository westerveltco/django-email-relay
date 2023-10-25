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

## License

`django-email-relay` is licensed under the MIT license. See the [`LICENSE`](LICENSE) file for more information.

## Inspiration

This package is heavily inspired by the [`django-mailer`](https://github.com/pinax/django-mailer) package. `django-mailer` is licensed under the MIT license, which is also the license used for this package. The required copyright notice is included in the [`LICENSE`](LICENSE) file for this package.
