# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project attempts to adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

Initial release!

### Added

- An email backend that stores emails in a database ala a Message model rather than sending them via SMTP or other means
- A database backend that routes writes to the Message model to a separate database
- A Message model that stores the contents of an email
- A relay service intended to be run separately, either as a standalone Docker image or as a management command within a Django project
- Initial documentation (README.md)
- Initial tests
- Initial CI/CD (GitHub Actions)

[unreleased]: https://github.com/westerveltco/django-email-relay/compare/HEAD...HEAD
[0.1.0]: https://github.com/westerveltco/django-email-relay/releases/tag/v0.1.0rc1
