# Test Suite for Grokipedia MCP Client

This directory contains tests for the Grokipedia MCP scraper library.

## Test Structure

- `test_client.py` - Unit tests for the GrokipediaScraper class
- `conftest.py` - Pytest configuration and shared fixtures
- `__init__.py` - Python package marker

## Test Coverage

The test suite covers:

### GrokipediaScraper Functionality
- Successful HTML parsing and section extraction
- Handling of different HTML structures (h1-h6, p, span, ul/ol/li)
- URL formatting for page titles
- HTTP error handling and graceful failure
- Edge cases (empty content, malformed HTML)

## Running Tests

### Prerequisites

Install test dependencies:

```bash
# From grokipedia_mcp directory
pip install -r requirements.txt
pip install -e ".[test]"
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test method
pytest tests/test_client.py::TestGrokipediaScraper::test_scrape_sections_success -v

# Run with coverage report
pytest --cov=grokipedia_client --cov-report=html
```

## Test Environment

Tests use mocked HTTP requests to avoid making network calls during testing. The test suite includes:

- Mock HTML fixtures for consistent test data
- Error scenario testing
- Different HTML structure variations
- URL formatting validation

## Adding New Tests

When adding new tests:

1. Follow the existing naming convention (`test_*`)
2. Include docstrings explaining test scenarios
3. Use the provided fixtures in `conftest.py`
4. Mock `requests.get` calls appropriately
5. Test both success and error scenarios

## Configuration

Test configuration is managed through `pyproject.toml` in the parent directory.
