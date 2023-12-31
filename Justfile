set dotenv-load := true

@_default:
    just --list

##################
#  DEPENDENCIES  #
##################

bootstrap:
    python -m pip install --editable '.[dev,hc,relay]'

pup:
    python -m pip install --upgrade pip

update:
    @just pup
    @just bootstrap

venv PY_VERSION="3.11.5":
    #!/usr/bin/env python
    from __future__ import annotations

    import subprocess
    from pathlib import Path

    PY_VERSION = "{{ PY_VERSION }}"
    name = f"relay-{PY_VERSION}"

    home = Path.home()

    pyenv_version_dir = home / ".pyenv" / "versions" / PY_VERSION
    pyenv_virtualenv_dir = home / ".pyenv" / "versions" / name

    if not pyenv_version_dir.exists():
        subprocess.run(["pyenv", "install", PY_VERSION], check=True)

    if not pyenv_virtualenv_dir.exists():
        subprocess.run(["pyenv", "virtualenv", PY_VERSION, name], check=True)

    (python_version_file := Path(".python-version")).write_text(name)

##################
#  TESTING/TYPES #
##################

test:
    python -m nox --reuse-existing-virtualenvs

coverage:
    python -m nox --reuse-existing-virtualenvs --session "coverage"

types:
    python -m nox --reuse-existing-virtualenvs --session "mypy"

##################
#     DJANGO     #
##################

manage *COMMAND:
    #!/usr/bin/env python
    import sys

    try:
        from django.conf import settings
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    settings.configure(INSTALLED_APPS=["email_relay"])
    execute_from_command_line(sys.argv + "{{ COMMAND }}".split(" "))

alias mm := makemigrations

makemigrations *APPS:
    @just manage makemigrations {{ APPS }}

migrate *ARGS:
    @just manage migrate {{ ARGS }}

shell:
    @just manage shell_plus

createsuperuser USERNAME="admin" EMAIL="" PASSWORD="admin":
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('{{ USERNAME }}', '{{ EMAIL }}', '{{ PASSWORD }}') if not User.objects.filter(username='{{ USERNAME }}').exists() else None" | python manage.py shell

##################
#     DOCKER     #
##################

testbuild:
    docker build -t relay:latest -f .dockerfiles/Dockerfile .

testrun *ARGS:
    docker run -it --rm -p 8000:8000 {{ ARGS }} relay:latest

createdb CONTAINER_NAME="relay_postgres" VERSION="15.3":
    #!/usr/bin/env python
    from __future__ import annotations

    import os
    import shutil
    import socket
    import subprocess
    import time
    from pathlib import Path

    CONTAINER_NAME = "{{ CONTAINER_NAME }}"
    VERSION = "{{ VERSION }}"


    def is_port_open(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) != 0


    def main():
        if not shutil.which("docker"):
            print("Docker is not installed")
            return

        if subprocess.getoutput(f"docker ps -q -f name={CONTAINER_NAME}"):
            print(f"Postgres container {CONTAINER_NAME} is already running")
        else:
            if subprocess.getoutput(
                f"docker ps -aq -f status=exited -f name={CONTAINER_NAME}"
            ):
                print(f"Starting postgres container {CONTAINER_NAME}")
                subprocess.run(["docker", "start", CONTAINER_NAME], check=True)
            else:
                print(f"Creating postgres container {CONTAINER_NAME}")
                port = 5432
                while not is_port_open(port):
                    print(f"Port {port} is already in use")
                    print("Incrementing port number by 1")
                    port += 1
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "--name",
                        CONTAINER_NAME,
                        "-e",
                        "POSTGRES_USER=postgres",
                        "-e",
                        "POSTGRES_PASSWORD=postgres",
                        "-e",
                        "POSTGRES_DB=postgres",
                        "-p",
                        f"{port}:5432",
                        "-d",
                        f"postgres:{VERSION}",
                    ],
                    check=True,
                )

        port_output = subprocess.getoutput(f"docker port {CONTAINER_NAME} 5432")
        port = port_output.split(":")[1]
        DATABASE_URL = f"postgres://postgres:postgres@localhost:{port}/postgres"
        os.environ["DATABASE_URL"] = DATABASE_URL

        env_file = Path(".env")
        if env_file.exists():
            print("Updating DATABASE_URL in .env file")
            content = env_file.read_text()
            content = content.replace("DATABASE_URL=.*", f"DATABASE_URL={DATABASE_URL}")
            env_file.write_text(content)
        else:
            print("Creating .env file")
            env_file.write_text(f"DATABASE_URL={DATABASE_URL}\n")

        while True:
            ready = (
                subprocess.run(
                    [
                        "docker",
                        "exec",
                        "-it",
                        CONTAINER_NAME,
                        "pg_isready",
                        "-U",
                        "postgres",
                        "-q",
                    ]
                ).returncode
                == 0
            )
            if ready:
                break
            print("Waiting for postgres to start")
            time.sleep(1)

        subprocess.run(["just", "manage", "migrate"], check=True)
        subprocess.run(["just", "createsuperuser"], check=True)


    raise SystemExit(main())

##################
#     DOCS       #
##################

@docs-install:
    python -m pip install '.[docs]'

@docs-serve:
    #!/usr/bin/env sh
    if [ -f "/.dockerenv" ]; then
        sphinx-autobuild docs docs/_build/html --host "0.0.0.0"
    else
        sphinx-autobuild docs docs/_build/html --host "localhost"
    fi

@docs-build LOCATION="docs/_build/html":
    sphinx-build docs {{ LOCATION }}

##################
#     UTILS      #
##################

lint:
    python -m nox --reuse-existing-virtualenvs --session "lint"

mypy:
    python -m nox --reuse-existing-virtualenvs --session "mypy"
