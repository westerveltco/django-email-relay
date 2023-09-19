# Generated by Django 4.2.5 on 2023-09-19 15:12

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Message",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("data", models.JSONField()),
                (
                    "priority",
                    models.PositiveSmallIntegerField(
                        choices=[(1, "Low"), (2, "Medium"), (3, "High")], default=1
                    ),
                ),
                (
                    "status",
                    models.PositiveSmallIntegerField(
                        choices=[
                            (1, "Queued"),
                            (2, "Deferred"),
                            (3, "Sent"),
                            (4, "Failed"),
                        ],
                        default=1,
                    ),
                ),
                ("retry_count", models.PositiveSmallIntegerField(default=0)),
                (
                    "log",
                    models.TextField(
                        blank=True,
                        help_text="Most recent log message from the email backend, if any.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
