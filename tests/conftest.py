"""Pytest configuration and shared fixtures."""

import os
import sys

import pytest

# Add project root to path to enable imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
