from __future__ import annotations

import os
from unittest import mock

from email_relay.checks import RELAY_CHECK_TAG
from email_relay.service import coerce_dict_values
from email_relay.service import default_settings
from email_relay.service import env_vars_to_nested_dict
from email_relay.service import filter_valid_django_settings
from email_relay.service import get_user_settings_from_env
from email_relay.service import merge_with_defaults
from email_relay.service import run_relay_service


def test_env_vars_to_nested_dict():
    env_vars = {
        "DATABASES__default__CONN_MAX_AGE": 600,
        "DEBUG": "True",
    }

    assert env_vars_to_nested_dict(env_vars) == {
        "DATABASES": {
            "default": {
                "CONN_MAX_AGE": 600,
            }
        },
        "DEBUG": "True",
    }


def test_merge_with_defaults():
    default_settings = {
        "DATABASES": {
            "default": {
                "CONN_MAX_AGE": 600,
            }
        },
        "DEBUG": False,
    }
    user_settings = {
        "DATABASES": {
            "default": {
                "CONN_MAX_AGE": 300,
            }
        },
        "DEBUG": True,
    }

    assert merge_with_defaults(default_settings, user_settings) == {
        "DATABASES": {
            "default": {
                "CONN_MAX_AGE": 300,
            }
        },
        "DEBUG": True,
    }


def test_get_user_settings_from_env():
    env_vars = {
        "DATABASES__default__CONN_MAX_AGE": "600",
        "DEBUG": "True",
        "INVALID_KEY": "True",
    }
    for k, v in env_vars.items():
        os.environ[k] = v

    assert get_user_settings_from_env() == {
        "DATABASES": {
            "default": {
                "CONN_MAX_AGE": 600,
            }
        },
        "DEBUG": True,
    }

    for k in env_vars:
        del os.environ[k]


def test_coerce_dict_values():
    types_dict = {
        "BOOLEAN": "True",
        "INTEGER": "600",
        "STRING": "str",
        "FLOAT": "3.14",
        "NONE": "None",
    }

    d = {
        **types_dict,
        "NESTED": types_dict,
    }

    assert coerce_dict_values(d) == {
        "BOOLEAN": True,
        "INTEGER": 600,
        "STRING": "str",
        "FLOAT": 3.14,
        "NONE": None,
        "NESTED": {
            "BOOLEAN": True,
            "INTEGER": 600,
            "STRING": "str",
            "FLOAT": 3.14,
            "NONE": None,
        },
    }


def test_storage_environment_override_preserves_django_default():
    settings = merge_with_defaults(
        default_settings,
        {
            "STORAGES": {
                "email_relay": {
                    "BACKEND": "example.SharedStorage",
                }
            }
        },
    )

    assert "default" in settings["STORAGES"]
    assert settings["STORAGES"]["email_relay"] == {"BACKEND": "example.SharedStorage"}


def test_standalone_service_checks_before_migrating():
    with (
        mock.patch("email_relay.service.argparse.ArgumentParser.parse_args"),
        mock.patch("email_relay.service.get_user_settings_from_env", return_value={}),
        mock.patch("django.conf.LazySettings.configure"),
        mock.patch("email_relay.service.django.setup"),
        mock.patch(
            "email_relay.service.resolved_database_alias", return_value="default"
        ),
        mock.patch("email_relay.service.call_command") as call_command,
    ):
        assert run_relay_service() == 0

    assert call_command.call_args_list == [
        mock.call("check", tags=[RELAY_CHECK_TAG], deploy=True),
        mock.call("migrate", database="default"),
        mock.call("runrelay"),
    ]


def test_filter_valid_django_settings():
    d = {
        "DEBUG": True,
        "INVALID_KEY": "invalid value",
        "DJANGO_EMAIL_RELAY": {
            "VALID_KEY": "valid value",
        },
    }

    assert filter_valid_django_settings(d) == {
        "DEBUG": True,
        "DJANGO_EMAIL_RELAY": {
            "VALID_KEY": "valid value",
        },
    }
