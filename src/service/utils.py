from __future__ import annotations

import copy
import os
from typing import Any

from django.conf import global_settings

from email_relay.conf import EMAIL_RELAY_SETTINGS_NAME


def get_user_settings_from_env() -> dict[str, Any]:
    """Get user-defined Django settings from environment variables.

    Returns:
        dict[str, Any]: Filtered and coerced dictionary containing valid Django settings.

    Example:
        >>> import os
        >>> os.environ['DEBUG'] = 'False'
        >>> get_user_settings_from_env()
        {'DEBUG': False}
    """
    all_env_vars = {k: v for k, v in os.environ.items()}
    env_vars_dict = env_vars_to_nested_dict(all_env_vars)
    valid_settings = filter_valid_django_settings(env_vars_dict)
    return coerce_dict_values(valid_settings)


def env_vars_to_nested_dict(env_vars: dict[str, Any]) -> dict[str, Any]:
    """Convert environment variables to a nested dictionary.

    Args:
        env_vars (dict[str, Any]): Dictionary of environment variables.

    Returns:
        dict[str, Any]: Nested dictionary derived from environment variables.

    Example:
        >>> env_vars_to_nested_dict({'DATABASES__default__ENGINE': 'django.db.backends.sqlite3'})
        {'DATABASES': {'default': {'ENGINE': 'django.db.backends.sqlite3'}}}
    """
    config: dict[str, Any] = {}
    for key, value in env_vars.items():
        keys = key.split("__")
        d = config
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
    return config


def filter_valid_django_settings(d: dict[str, Any]) -> dict[str, Any]:
    """Filter dictionary to only include valid Django settings.

    Args:
        d (dict[str, Any]): Input dictionary.

    Returns:
        dict[str, Any]: Filtered dictionary.

    Example:
        >>> filter_valid_django_settings({'DEBUG': True, 'INVALID_KEY': "invalid value"})
        {'DEBUG': True}
    """
    valid_settings = set(dir(global_settings))
    valid_settings.add(EMAIL_RELAY_SETTINGS_NAME)
    return {k: v for k, v in d.items() if k in valid_settings}


def coerce_dict_values(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively coerces dictionary values to the appropriate type.

    Args:
        d (dict[str, Any]): Input dictionary.

    Returns:
        dict[str, Any]: Dictionary with values coerced.

    Example:
        >>> coerce_dict_values({'DEBUG': 'True', 'DATABASES': {'default': {'ENGINE': 'str', 'CONN_MAX_AGE': '600'}}})
        {'DEBUG': True, 'DATABASES': {'default': {'ENGINE': 'str', 'CONN_MAX_AGE': 600}}}
    """
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = coerce_dict_values(value)
        else:
            if value.lower() == "true":
                d[key] = True
            elif value.lower() == "false":
                d[key] = False
            elif value.lower() == "none":
                d[key] = None
            elif value.isdigit():
                d[key] = int(value)
            elif value.replace(".", "", 1).isdigit():
                d[key] = float(value)
            else:
                d[key] = value
    return d


def merge_with_defaults(
    default_dict: dict[str, Any], override_dict: dict[str, Any]
) -> dict[str, Any]:
    """Merge two dictionaries, updating and merging nested dictionaries. The override_dict takes precedence.

    Args:
        default_dict (dict[str, Any]): The dictionary containing default settings.
        override_dict (dict[str, Any]): The dictionary containing settings that should override the defaults.

    Returns:
        dict[str, Any]: Merged dictionary.

    Example:
        >>> default_dict = {'DEBUG': False, 'DATABASES': {'default': {'ENGINE': 'django.db.backends.sqlite3', 'CONN_MAX_AGE': 600}}}
        >>> override_dict = {'DEBUG': True, 'DATABASES': {'default': {'ENGINE': 'django.db.backends.postgresql'}}}
        >>> merge_with_defaults(default_dict, override_dict)
        {'DEBUG': True, 'DATABASES': {'default': {'ENGINE': 'django.db.backends.postgresql', 'CONN_MAX_AGE': 600}}}
    """
    return_dict = copy.deepcopy(default_dict)

    for key, value in override_dict.items():
        if isinstance(value, dict) and isinstance(return_dict.get(key), dict):
            return_dict[key] = merge_with_defaults(return_dict[key], value)
        else:
            return_dict[key] = value

    return return_dict
