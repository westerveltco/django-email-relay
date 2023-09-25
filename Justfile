set dotenv-load := true

@_default:
    just --list

##################
#  DEPENDENCIES  #
##################

install:
    python -m pip install --editable '.[dev]'

pup:
    python -m pip install --upgrade pip

update:
    @just pup
    @just install

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
    rm -rf .coverage htmlcov
    pytest -vv
    python -m coverage html --skip-empty  # --skip-covered
    python -m coverage report --fail-under=100

types:
    python -m mypy .

##################
#     DJANGO     #
##################

manage *COMMAND:
    python -m manage {{ COMMAND }}

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

enter CONTAINER="relay[-_]devcontainer[-_]app" SHELL="zsh" WORKDIR="/workspace" USER="vscode":
    #!/usr/bin/env sh
    if [ -f "/.dockerenv" ]; then
        echo "command cannot be run from within a Docker container"
    else
        case {{ SHELL }} in
            "zsh" )
                shell_path="/usr/bin/zsh" ;;
            "bash" )
                shell_path="/bin/bash" ;;
            "sh" )
                shell_path="/bin/sh" ;;
            * )
                shell_path="/usr/bin/zsh" ;;
        esac

        container=$(docker ps --filter "name={{ CONTAINER }}" --format "{{{{.Names}}")

        docker exec -it -u {{ USER }} -w {{ WORKDIR }} $container $shell_path
    fi

testbuild:
    docker build -t relay:latest .

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
#    ENV SYNC    #
##################

envsync:
    #!/usr/bin/env python
    from pathlib import Path

    envfile = Path('.env')
    envfile_example = Path('.env.example')

    if not envfile.exists():
        envfile.write_text(envfile_example.read_text())

    with envfile.open() as f:
        lines = [line for line in f.readlines() if not line.endswith('# envsync: ignore\n')]
        lines = [line.split('=')[0] + '=\n' if line.endswith('# envsync: no-value\n') else line for line in lines]

        lines.sort()
        envfile_example.write_text(''.join(lines))

##################
#     UTILS      #
##################

lint:
    python -m nox --reuse-existing-virtualenvs --session "lint"

mypy:
    python -m nox --reuse-existing-virtualenvs --session "mypy"
