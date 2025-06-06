# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project attempts to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## [${version}]
### Added - for new features
### Changed - for changes in existing functionality
### Deprecated - for soon-to-be removed features
### Removed - for now removed features
### Fixed - for any bug fixes
### Security - in case of vulnerabilities
[${version}]: https://github.com/westerveltco/django-email-relay/releases/tag/v${version}
-->

## [Unreleased]

## [0.6.0]

### Added

- Added support for Python 3.13.

### Changed

- Now using `uv` for project management.
- Email relay `Dockerfile` service reorganized to take advantage of `uv` and it's features.
- Email relay service standalone package has been removed and moved to a module within the `email_relay` package.

### Removed

- Dropped support for Django 5.0.
- `[dev]`, `[docs]`, and `[lint]` extras have been removed and migrated to `[dependency-groups]`.

### Fixed

- In the email relay service, any `Exception` beyond SMTP transport errors now fails the message instead of raising the `Exception`. This allows the relay service to stay operational and sending messages that are OK, while any messages that are causing errors will be failed immediately.

## [0.5.0]

### Added

- Added support for Django 5.1 and 5.2.

### Changed

- Now using v2024.18 of `django-twc-package`.

### Removed

- Dropped support for Python 3.8.
- Dropped support for Django 3.2.

## [0.4.3]

### Fixed

- Added all documentation pages back to `toctree`.
- Added back missing copyright information from `django-mailer`. Sorry to all the maintainers and contributors of that package! It was a major oversight.
- Added back all missing extras: `hc`, `psycopg`, and `relay`.

## [0.4.2]

### Fixed

- Added `LICENSE` to `Dockerfile`.

## [0.4.1]

### Fixed

- Added back Docker publishing to `release.yml` GitHub Actions workflow.

## [0.4.0]

### Added

- A `_email_relay_version` field to `RelayEmailData` to track the version of the schema used to serialize the data. This should allow for future changes to the schema to be handled more gracefully.

### Changed

- Now using [`django-twc-package`](https://github.com/westerveltco/django-twc-package) template for repository and package structure.
    - This includes using `uv` internally for managing Python dependencies.

### Fixed

- Resolved a type mismatch error in from_email_message method when encoding attachments to base64. Added type checking to confirm that the payload extracted from a MIMEBase object is of type bytes before passing it to base64.b64encode.

## [0.3.0]

### Added

- Support for Django 5.0.

### Removed

- Support for Django 4.1.

## [0.2.1]

### Fixed

- Migration 0002 was not being applied to the `default` database, which is the norm when running the relay in Docker.

## [0.2.0] - **YANKED**

This release has been yanked from PyPI due to a bug in the migration that was not caught.

**This release involves migrations.** Please read below for more information.

### Added

- A `RelayEmailData` dataclass for representing the `Message.data` field.
- Documentation in the package's deprecation policy about the road to 1.0.0.
- Complete test coverage for all of the public ways of sending emails that Django provides.

### Changed

- **Breaking**: The internal JSON schema for the `Message.data` field has been updated to bring it more in line with all of the possible fields provided by Django's `EmailMessage` and `EmailMultiAlternatives`. This change involves a migration to update the `Message.data` field to the new schema. This is a one-way update and cannot be rolled back. Please take care when updating to this version and ensure that all projects using `django-email-relay` are updated at the same time. See the [updating](https://django-email-relay.westervelt.dev/en/latest/updating.html) documentation for more information.
- The internal `AppSettings` dataclass is now a `frozen=True` dataclass.

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

### New Contributors

- Josh Thomas <josh@joshthomas.dev> (maintainer)
- Jeff Triplett [@jefftriplett](https://github.com/jefftriplett)

### Thanks ❤️

Big thank you to the original authors of [`django-mailer`](https://github.com/pinax/django-mailer) for the inspiration and for doing the hard work of figuring out a good way of queueing emails in a database in the first place.

[unreleased]: https://github.com/westerveltco/django-email-relay/compare/v0.6.0...HEAD
[0.1.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.1.0
[0.1.1]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.1.1
[0.2.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.2.0
[0.2.1]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.2.1
[0.3.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.3.0
[0.4.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.4.0
[0.4.1]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.4.1
[0.4.2]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.4.2
[0.4.3]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.4.3
[0.5.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.5.0
[0.6.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.6.0
