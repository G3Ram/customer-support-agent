"""Integration test configuration.

This module loads environment variables from backend/.env
and provides common fixtures for integration tests.
"""

from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
