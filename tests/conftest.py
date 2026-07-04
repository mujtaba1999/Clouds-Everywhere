"""Shared pytest fixtures/paths so tests import the flat modules cleanly."""
import os
import sys

# Make the project root importable (aoi.py, query.py, ... live at the top level)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
