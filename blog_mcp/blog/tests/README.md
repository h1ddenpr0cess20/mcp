# Test Suite for the Blog

This directory contains tests for the blog application: its storage and rules, Markdown rendering, login and sessions, uploads, the website, and the JSON API.

## Test Structure

- `test_store.py` - Unit tests for BlogStore (posts, validation, versions and conflicts, search, tags)
- `test_render.py` - Unit tests for Markdown rendering and plain-text helpers
- `test_auth.py` - Sessions, CSRF tokens, API token, and login lockout
- `test_passwords.py` - Password hashing, the hash file, and migrating an old plaintext file
- `test_credentials.py` - How the blog finds its credential at startup, and proof the password is never stored
- `test_cli.py` - `blog.py` first start, `set-password`, and `hash-password`, including the real program as a subprocess
- `test_media.py` - Image validation and storage
- `test_config.py` - Settings and generated secrets
- `test_site.py` - The website, login, admin editor, uploads, and headers, over real HTTP
- `test_api.py` - The JSON API, over real HTTP
- `conftest.py` - Shared fixtures and a small cookie-aware HTTP client

## Test Coverage

### Security
- Every reading page and admin page needs a login (private mode); public mode exposes published posts only
- Wrong, missing, malformed, and forged credentials; lockout after repeated failures; no redirect to other sites after login
- A CSRF token is required on every state-changing form and background request
- The API token and the browser login are separate credentials
- Hostile titles, tags, summaries, bodies, and search text are escaped on every page; scripts in posts never run
- Uploads are checked by content (SVG, HTML, and executables are refused), size-limited even when chunked, and cannot be used to read other files
- Owner-only permissions on the data directory, database, and secrets
- The login password is stored only as a salted hash: it is found nowhere in the data folder, in any response, or in the app's memory, and an old plaintext password file is converted and deleted on upgrade

### Behavior
- Writing, editing, publishing, unpublishing, and deleting through both the website and the API
- A post changed elsewhere is never silently overwritten, and the editor keeps your text
- Pagination, tags, search, and drafts staying out of public lists

## Running Tests

### Prerequisites

```bash
# From the blog directory
pip install -r requirements.txt
pip install -e ".[test]"
```

### Basic Test Execution

```bash
# Run all tests (about a minute: most tests start a real server)
pytest

# Run only the fast tests that need no server
pytest -m unit

# Run one file or test
pytest tests/test_api.py
pytest tests/test_site.py::TestCsrf -v

# Run with coverage report
pytest --cov=blog_app --cov-report=html
```

## Test Environment

Tests run the blog under uvicorn on a free local port with a fresh data directory in a pytest temp folder, so they never touch `~/mcp-blog` or collide with a running blog. They use only the standard library to make requests, so no extra test dependencies are needed. No network access is required.

## Adding New Tests

1. Follow the existing naming convention (`test_*`) and markers (`unit`, `integration`)
2. Use the `site`, `public_site`, and `admin` fixtures for anything that needs the running blog
3. For anything that renders user content, include a hostile input
4. For anything that changes state, test that it is refused without a login and without a CSRF token

## Configuration

Test configuration is managed through `pyproject.toml` in the parent directory.
