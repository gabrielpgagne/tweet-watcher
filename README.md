# stock watcher

## Setup

Install [ollama](https://ollama.com), then setup this project:

- `uv venv`
- `source .venv/bin/activate`
- `uv sync`
  
## Env file

The project loads a few configurations from an env file located in the root of the project `path/to/project/.env`:

```bash
TRUTHSOCIAL_USERNAME="foo"
TRUTHSOCIAL_PASSWORD="bar"
TRUTHSOCIAL_HANDLE="realDonaldTrump"
NTFY_TOPIC="my-ntfy-topic"
OLLAMA_MODEL="llama3.2:3b"
```