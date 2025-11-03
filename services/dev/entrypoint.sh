#!/usr/bin/env bash
set -e

# Install as editable package the project under /workspace
# Ignore errors to allow the dev container to start even if the project is not
# in a valid state. We do not need to install dependencies here as they are
# installed in the Dockerfile. If the user makes changes to the dependencies,
# they'll need to either rebuild the container or `uv sync` to install them.
uv pip install -e /workspace || true


# Run any additional commands passed and replace the shell with the command
if [ $# -gt 0 ]; then
    exec "$@"
fi
