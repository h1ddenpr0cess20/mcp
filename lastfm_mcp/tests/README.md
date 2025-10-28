# Test Suite for Last.fm MCP Client

This directory contains comprehensive tests for the Last.fm MCP client library.

## Test Structure

- `test_client.py` - Main test file containing unit tests for all API classes
- `conftest.py` - Pytest configuration and shared fixtures
- `__init__.py` - Python package marker

## Test Coverage

The test suite covers:

### Base Functionality (`LastfmAPIBase`)
- API key initialization (environment variables and explicit)
- API signature generation for authenticated requests
- GET and POST request handling
- Error handling for missing credentials
- HTTP error propagation

### API Classes
- **AlbumAPI**: Album information, tags, search
- **ArtistAPI**: Artist information, similar artists, top albums/tracks, search
- **AuthAPI**: Authentication (tokens, sessions, mobile sessions)
- **ChartAPI**: Top artists, tracks, and tags charts
- **GeoAPI**: Geographic charts by country/location
- **LibraryAPI**: User's music library
- **TagAPI**: Tag information, similar tags, top content
- **TrackAPI**: Track information, scrobbling, love/unlove, now playing
- **UserAPI**: User profiles, recent tracks, top artists/albums/tracks

## Running Tests

### Prerequisites

Install test dependencies:

```bash
# Using pip with requirements file
pip install -r requirements.txt
pip install -e ".[test]"

# Or install directly
pip install pytest pytest-cov pytest-mock
```

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test class
pytest tests/test_client.py::TestAlbumAPI -v

# Run specific test method
pytest tests/test_client.py::TestAlbumAPI::test_get_info -v

# Run with coverage report
pytest --cov=lastfm_client --cov-report=html

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration
```

### Test Markers

- `@pytest.mark.unit` - Unit tests (default)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow running tests

## Test Environment

Tests use mocked HTTP requests to avoid making actual API calls during testing. The test suite includes:

- Mock response fixtures for consistent test data
- Environment cleanup to prevent test interference
- Comprehensive error scenario testing
- Authentication state testing

## Adding New Tests

When adding new tests:

1. Follow the existing naming convention (`test_*`)
2. Use descriptive test method names
3. Include docstrings explaining what each test validates
4. Use the provided fixtures in `conftest.py`
5. Mock external dependencies appropriately
6. Test both success and error scenarios

## Configuration

Test configuration is managed through:

- `pyproject.toml` - Pytest settings and markers
- `conftest.py` - Shared fixtures and hooks
- Environment variables for test isolation

## Continuous Integration

The test suite is designed to run in CI environments with:

- No external API dependencies
- Deterministic test results
- Comprehensive coverage reporting
- Fast execution times
