# Test Suite for Blog MCP Client

This directory contains tests for the Blog MCP storage layer, Markdown renderer, password-protected viewer, and FastMCP tools.

## Test Structure

- `test_client.py` - Unit tests for the BlogClient class (storage, validation, search, tags)
- `test_render.py` - Unit tests for Markdown rendering and plain-text helpers
- `test_web.py` - Tests for the BlogServer viewer over real local HTTP/HTTPS connections
- `test_server.py` - Tests for the FastMCP tools in `server.py`, driven through an in-memory MCP client
- `conftest.py` - Pytest configuration and shared fixtures
- `__init__.py` - Python package marker

## Test Coverage

The test suite covers:

### BlogClient Functionality
- Creating, reading, listing, updating, publishing, and deleting posts
- Slug generation, uniqueness, and renaming; tag normalization
- Find-and-replace edits, including ambiguous and missing matches
- Case-insensitive search (including non-ASCII), snippets, and SQL metacharacters
- Input limits, rejected input leaving the blog unchanged, and persistence across restarts
- Owner-only permissions on the data directory and database

### Rendering
- Raw HTML and dangerous link schemes (`javascript:`, `data:`) are neutralized
- Tables, strikethrough, excerpts, and word counts

### Viewer
- Every route rejects missing, wrong, and malformed credentials
- Generated, persisted, and configured passwords; the password is never written to disk when configured
- Drafts hidden from the home page; tag, search, and pagination pages
- HTML escaping of titles, tags, summaries, and search text; path traversal and SQL injection attempts
- Security headers, HEAD requests, read-only behavior, port conflicts, and shutdown
- HTTPS with a generated certificate (skipped if `openssl` is unavailable)

### MCP Tools
- Every tool's happy path and error messages
- Tool schemas stay simple (no `anyOf`) for local-LLM compatibility
- `get_blog_info` never reveals the password
- A post written through a tool is served at the returned URL, only with credentials

## Running Tests

### Prerequisites

Install test dependencies:

```bash
# From blog_mcp directory
pip install -r requirements.txt
pip install -e ".[test]"
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only the fast tests that need no sockets
pytest -m unit

# Run specific test method
pytest tests/test_client.py::TestSearch::test_every_word_must_match -v

# Run with coverage report
pytest --cov=blog_client --cov-report=html
```

## Test Environment

Tests use a fresh SQLite database in a pytest temp directory and start viewers on ephemeral ports (`port=0`), so they never touch `~/mcp-blog` and never collide with a running server. No network access is needed. The suite includes:

- A `clock` fixture that freezes timestamps for deterministic ordering
- A `viewer` fixture running a real server with known credentials
- Helpers for authenticated and unauthenticated requests

## Adding New Tests

When adding new tests:

1. Follow the existing naming convention (`test_*`) and markers (`unit`, `integration`)
2. Include docstrings explaining test scenarios
3. Use the provided fixtures in `conftest.py`
4. Never point a test at the default data directory or a fixed port
5. Test both success and error scenarios, and for anything the viewer renders, a hostile input

## Configuration

Test configuration is managed through `pyproject.toml` in the parent directory.
