"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

import pytest

# Add project root to path to enable imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
