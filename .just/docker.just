set unstable := true

justfile := justfile_directory() + "/.just/docker.just"

[private]
default:
    @just --list --justfile {{ justfile }}

[private]
fmt:
    @just --fmt --justfile {{ justfile }}

[no-cd]
build:
    docker build --tag docker-email-relay:local .

[no-cd]
run *ARGS: build
    docker run --rm docker-email-relay:local {{ ARGS }}

[no-cd]
smoke:
    @just docker run uv run -m email_relay.service --help
