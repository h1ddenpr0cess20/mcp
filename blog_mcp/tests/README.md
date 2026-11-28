# Test Suite for Blog MCP Client

This directory contains tests for the Blog MCP server: the API client, the FastMCP tools, and (when the blog is available) the whole thing working against the real blog.

## Test Structure

- `test_client.py` - Unit tests for the BlogClient class (requests, configuration, errors)
- `test_server.py` - Tests for the FastMCP tools in `server.py`, driven through an in-memory MCP client against a fake blog
- `test_integration.py` - The MCP server against the real blog application over real HTTP
- `conftest.py` - Pytest configuration and shared fixtures
- `__init__.py` - Python package marker

## Test Coverage

The test suite covers:

### BlogClient Functionality
- Configuration from the environment, including finding the API token in the blog's data directory
- The exact requests sent for each operation, with the token on every request and no redirects followed
- Slugs with special characters cannot alter the request path
- Every failure mode: wrong token, blog down, timeout, bad certificate, redirect, a non-blog server, and the blog's own error messages
- Errors never echo the token

### MCP Tools
- Each tool's arguments map to the right API call; `update_post` sends only what was asked for
- The server stores nothing and serves nothing; importing it makes no requests
- `get_blog_info` reports a stopped blog as an answer, and a wrong token as an error
- Tool schemas stay simple (no `anyOf`) for local-LLM compatibility

### Integration (needs the blog's dependencies)
- A post written by a tool appears on the website, and edits, unpublishing, and deleting show up at once
- A post written in the browser editor is readable by a tool
- Image upload, error messages from the blog, search, tags, and a wrong token
- The blog keeps serving when the MCP server cannot reach it

## Running Tests

### Prerequisites

Install test dependencies:

```bash
# From blog_mcp directory
pip install -r requirements.txt
pip install -e ".[test]"
```

The integration tests need the blog application (the `blog` folder in this package) and its dependencies (`pip install -r blog/requirements.txt`). FastMCP already installs most of them, so they usually run; if anything is missing that file is skipped and everything else still runs.

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only the tests that need no blog
pytest -m unit

# Run specific test method
pytest tests/test_client.py::TestErrors::test_a_rejected_token_says_what_to_check -v

# Run with coverage report
pytest --cov=blog_client --cov-report=html
```

## Test Environment

Unit and tool tests never touch the network: they answer the client's requests from a fake. The integration tests start the real blog on a free local port with a temporary data directory, so they never touch `~/mcp-blog` or a running blog.

## Adding New Tests

1. Follow the existing naming convention (`test_*`) and markers (`unit`, `integration`)
2. Use the `make_client` fixture and `make_response` helper in `conftest.py` for anything that needs a fake blog
3. Test both success and error scenarios, and that a failure message tells the person what to do next

## Configuration

Test configuration is managed through `pyproject.toml` in the parent directory.
