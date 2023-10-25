# Updating

As `django-email-relay` involves database models and the potential for migrations, care should be taken when updating to ensure that all Django projects using `django-email-relay` are upgraded at roughly the same time. See the [deprecation policy](#deprecation-policy) for more information regarding backward incompatible changes.

When updating to a new version, it is recommended to follow the following steps:

1. Update the relay service to the new version. As part of the update process, the relay service should run any migrations that are needed. If using the provided Docker container, this is done automatically as Django's `migrate` command is baked into the image. When running the relay service from a Django project, you will need to run the `migrate` command yourself, either as part of your deployment strategy or manually.
2. Update all distributed projects to the new version.

## Deprecation Policy

Any changes that involve models and/or migrations, or anything else that is potentially backward incompatible, will be split across two or more releases:

1. A release that adds the changes in a backward compatible way, with a deprecation warning. This release will be tagged with a minor version bump, e.g., `0.1.0` to `0.2.0`.
2. A release that removes the backward compatible changes and removes the deprecation warning. This release will be tagged with a major version bump, e.g., `0.2.0` to `1.0.0`.

This is unlikely to happen often, but it is important to keep in mind when updating.

A major release does not necessarily mean that there are breaking changes or ones involving models and migrations. You should always check the [changelog](CHANGELOG.md) and a version's release notes for more information.
