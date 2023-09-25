from __future__ import annotations

from service import env_vars_to_nested_dict
from service import merge_dicts


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


def test_merge_dicts():
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

    assert merge_dicts(default_settings, user_settings) == {
        "DATABASES": {
            "default": {
                "CONN_MAX_AGE": 300,
            }
        },
        "DEBUG": True,
    }
