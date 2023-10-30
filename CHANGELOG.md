# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project attempts to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1]

### Added

- Moved a handful of common `Message` queries and actions from the `runrelay` management command to methods on the `MessageManager` class.

### Fixed

- The relay service would crash if requests raised an `Exception` during the healthcheck ping. Now it will log the exception and continue processing the queue.

## [0.1.0]

Initial release!

### Added

- An email backend that stores emails in a database ala a Message model rather than sending them via SMTP or other means.
    - Designed to work seamlessly with Django's built-in ways of sending emails.
- A database backend that routes writes to the Message model to a separate database.
- A Message model that stores the contents of an email.
    - The Message model stores the contents of the email as a JSONField.
    - Attachments are stored in the database, under the 'attachments' key in the JSONField.
        - Should be able to handle anything that Django can by default.
- A relay service intended to be run separately, either as a standalone Docker image or as a management command within a Django project.
    - A Docker image is provided for the relay service. Currently only PostgreSQL is supported as a database backend.
    - A management command is provided for the relay service. Any database backend supported by Django should work (minus SQLite which doesn't make sense for a relay service).
    - The relay service can be configured with a healthcheck url to ensure it is running.
- Initial documentation.
- Initial tests.
- Initial CI/CD (GitHub Actions).

### New Contributors!

- Josh Thomas <josh@joshthomas.dev> (maintainer)
- Jeff Triplett <@jefftriplett>

### Thanks ❤️

Big thank you to the original authors of [`django-mailer`](https://github.com/pinax/django-mailer) for the inspiration and for doing the hard work of figuring out a good way of queueing emails in a database in the first place.

[unreleased]: https://github.com/westerveltco/django-email-relay/compare/v0.1.1...HEAD
[0.1.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.1.0
[0.1.1]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.1.1
