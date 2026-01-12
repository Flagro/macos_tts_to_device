#!/bin/bash
# Script to run the test suite

set -e

echo "🧪 Running macOS TTS to Device Test Suite"
echo "=========================================="

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    uv pip install pytest pytest-cov pytest-mock
fi

echo ""
echo "📊 Running tests with coverage..."
pytest --cov=src --cov=cli --cov=gui --cov=settings \
       --cov-report=term-missing \
       --cov-report=html \
       -v

echo ""
echo "✅ Tests complete!"
echo ""
echo "📈 Coverage report saved to: htmlcov/index.html"
echo "   Open with: open htmlcov/index.html"
