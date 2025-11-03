# Subpar Async

This library is purely educational and demonstrates how to build an asynchronous
task scheduler in Python using generator-based coroutines.

See the `examples/` directory for usage examples.


## Quick Start

Setup the project:

```bash
git clone https://github.com/johntrimble/subpar-async.git
cd subpar-async
./script/bootstrap
docker compose build dev # will take a minute due to python build
```

Start the dev container:

```bash
docker compose up -d dev
```

Run the example echo server:

```bash
docker compose exec -it dev python examples/example_echo.py
```

From another terminal, connect using netcat:

```bash
docker compose exec -it dev nc localhost 2000
```

Type something and see it echoed back! Use `Ctrl-C` to exit.
