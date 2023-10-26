from __future__ import annotations

import os

from service.utils import coerce_dict_values
from service.utils import env_vars_to_nested_dict
from service.utils import filter_valid_django_settings
from service.utils import get_user_settings_from_env
from service.utils import merge_with_defaults


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

    for k in env_vars.keys():
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
