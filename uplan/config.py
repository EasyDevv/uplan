"""Central configuration settings for uPlan."""

from pathlib import Path

# Define base directories relative to the current working directory
CWD = Path.cwd()
INPUT_BASE_DIR = CWD / "input"
OUTPUT_BASE_DIR = CWD / "output"

# Ensure directories exist (optional, but good practice)
# INPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)
# OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

# You can add other configuration constants here as needed
# e.g., DEFAULT_MODEL = "gemma3:1b"
