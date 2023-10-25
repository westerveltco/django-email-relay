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


## License

`django-email-relay` is licensed under the MIT license. See the [`LICENSE`](LICENSE) file for more information.

## Inspiration

This package is heavily inspired by the [`django-mailer`](https://github.com/pinax/django-mailer) package. `django-mailer` is licensed under the MIT license, which is also the license used for this package. The required copyright notice is included in the [`LICENSE`](LICENSE) file for this package.
