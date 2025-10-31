# RapidAPI FastMCP Server

A modular MCP server built from the RapidAPI tools that were available in my [Tyumi](https://github.com/h1ddenpr0cess20/Tyumi) project.  
This collection contains all the endpoints that I had bothered to implement in that project before abandoning it.  
I will add more as boredom dictates.  
Feel free to add your own.

## Requirements

- Python 3.11 or newer
- A RapidAPI key with access to the endpoints

## Setup

1. *(Optional)* Create and activate a virtual environment.
2. Install the Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Provide your RapidAPI key. The client reads `RAPIDAPI_KEY` from the
   environment or an `.env` file in `python/`:

   ```bash
   # Either export the variable
   export RAPIDAPI_KEY="your-secret-key"

   # Or create python/.env with the same value
   echo 'RAPIDAPI_KEY=your-secret-key' >> python/.env
   ```

## Running the servers

### Run a single domain server

Pick a domain and start only that FastMCP instance. The server logs the host and
port on startup and blocks until you press `Ctrl+C`.

```bash
python server.py entertainment
```

You can override the binding interface or port if the default does not work for
your environment:

```bash
python server.py social --host 127.0.0.1 --port 9500
```

### Run every server at once

Launch all domain servers simultaneously with one command. Each server is
started in its own Python process on the default port listed below. Use
`Ctrl+C` to stop the orchestrator; any running child processes will be cleaned
up automatically.

```bash
python server.py --all
```

Pass `--host` if you need all services bound to a different interface:

```bash
python server.py --all --host 127.0.0.1
```

> `--port` is not supported with `--all` because every domain already has a
> dedicated port. Override ports only when launching individual servers.

## Default ports

| Domain        | Default port |
| ------------- | ------------ |
| jobs          | 9401         |
| finance       | 9402         |
| food          | 9403         |
| entertainment | 9404         |
| social        | 9405         |
| realestate    | 9406         |
| news          | 9407         |

These ports are configured in `python/servers/<domain>.py` and are used when
running `python server.py --all`. Adjust them directly in the module if
you need different defaults across the project.
