# Test Suite

This directory contains the test suite for macOS TTS to Device.

## Structure

```
tests/
├── conftest.py           # Pytest configuration and shared fixtures
├── test_tts_base.py      # Tests for base TTSEngine class
├── test_tts_say.py       # Tests for Say TTS engine
├── test_tts_bark.py      # Tests for Bark TTS engine
├── test_cli.py           # Tests for CLI interface
├── test_gui.py           # Tests for GUI application
└── test_settings.py      # Tests for settings module
```

## Running Tests

### Install Test Dependencies

First, install the development dependencies:

```bash
uv pip install .[dev]
```

Or install everything including Bark and tests:

```bash
uv pip install .[all]
```

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov=cli --cov=gui --cov=settings --cov-report=html
```

This generates a coverage report in `htmlcov/index.html`.

### Run Specific Test Files

```bash
# Test only TTS engines
pytest tests/test_tts_*.py

# Test only CLI
pytest tests/test_cli.py

# Test only GUI
pytest tests/test_gui.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Tests Matching Pattern

```bash
# Run tests with "initialization" in the name
pytest -k initialization

# Run tests excluding GUI tests
pytest -m "not gui"
```

## Test Coverage

Current test coverage includes:

- ✅ **TTSEngine Base Class**: Initialization, device listing, audio processing
- ✅ **Say Engine**: Initialization, audio generation, timeout handling
- ✅ **Bark Engine**: Initialization, audio generation, voice validation
- ✅ **CLI Interface**: Help text, voice listing, text processing
- ✅ **GUI Application**: Initialization, engine switching, input validation
- ✅ **Settings**: Configuration validation

## Writing New Tests

When adding new tests:

1. Follow the naming convention: `test_*.py` for files, `test_*` for functions
2. Use descriptive test names that explain what is being tested
3. Keep tests focused (one assertion per test when possible)
4. Use mocks to avoid side effects (file I/O, network, actual audio playback)
5. Add docstrings to explain complex test scenarios

## Continuous Integration

These tests are designed to run in CI/CD environments. They:

- Don't require audio hardware
- Don't require macOS-specific commands (they're mocked)
- Don't require network access
- Complete quickly (no actual TTS generation)
