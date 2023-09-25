from __future__ import annotations

import pytest
from django.core.management import call_command


def test_runrelay_help():
    # We'll capture the output of the command
    with pytest.raises(SystemExit) as exec_info:
        # call_command will execute our command as if we ran it from the command line
        # the 'stdout' argument captures the command output
        call_command("runrelay", "--help")

    # Asserting that the command exits with a successful exit code (0 for help command)
    assert exec_info.value.code == 0
