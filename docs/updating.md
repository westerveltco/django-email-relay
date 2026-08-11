# Updating

As `django-email-relay` involves database models and the potential for migrations, care should be taken when updating to ensure that all Django projects using `django-email-relay` are upgraded at roughly the same time. See the [deprecation policy](#deprecation-policy) for more information regarding backward incompatible changes.

When updating to a new version, it is recommended to follow the following steps:

1. Update the relay service to the new version. As part of the update process, the relay service should run any migrations that are needed. If using the provided Docker container, this is done automatically as Django's `migrate` command is baked into the image. When running the relay service from a Django project, you will need to run the `migrate` command yourself, either as part of your deployment strategy or manually.
2. Update all distributed projects to the new version.

## Stored attachment rollout

The attachment-storage change spans two package releases.

Release A adds the `MessageAttachment` schema and a relay reader for both legacy JSON attachments and stored attachments. Its producers keep writing the legacy JSON shape. Before upgrading a relay to Release A:

1. configure `STORAGES["email_relay"]` on every relay;
2. point every relay at the same physical storage;
3. grant read access now and plan create, list, and delete access for Release B;
4. set a finite `EMAIL_MAX_RETRIES` if permanently missing objects should eventually fail;
5. deploy the relay and run the schema-only migration against `DJANGO_EMAIL_RELAY["DATABASE_ALIAS"]`, using `migrate --database email_relay_db` for the default hosted-project alias.

Producer projects may upgrade to Release A later and continue writing JSON. Do not enable a file-writing producer until every relay runs at least Release A. After the first stored message is written, Release A is the oldest safe relay rollback target.

Release B will switch producers to stored attachments and add backfill and cleanup commands. Upgrade all relays to Release B before upgrading one canary producer, then upgrade every active and dormant producer. A Release B producer may roll back to Release A and resume JSON writes; a relay must never roll back below Release A after stored writes begin.

The legacy reader remains until production shows no legacy rows or fallback reads for the agreed deployment, queue, retry, retention, and rollback window. Do not treat the Release A schema migration as a data backfill: it performs no storage I/O and leaves existing rows unchanged.

Release A does not add producer-side Django 6 `MIMEPart` support. That support arrives with the Release B writer.

## Deprecation Policy

```{admonition} Road to v1.0.0
:class: warning

Before `django-email-relay` reaches version 1.0.0, the deprecation policy is a little more relaxed. See the [changelog](https://github.com/westerveltco/django-email-relay/blob/main/CHANGELOG.md) for more information regarding backward incompatible changes.
```

Any changes that involve models and/or migrations, or anything else that is potentially backward incompatible, will be split across two or more releases:

1. A release that adds the changes in a backward compatible way, with a deprecation warning. This release will be tagged with a minor version bump, e.g., `0.1.0` to `0.2.0`.
2. A release that removes the backward compatible changes and removes the deprecation warning. This release will be tagged with a major version bump, e.g., `0.2.0` to `1.0.0`.

This is unlikely to happen often, but it is important to keep in mind when updating.

A major release does not necessarily mean that there are breaking changes or ones involving models and migrations. You should always check the [changelog](CHANGELOG.md) and a version's release notes for more information.
