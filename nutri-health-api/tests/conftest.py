"""
Add the project root to sys.path so that `app.*` imports resolve
when running pytest from the nutri-health-api/ directory.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
