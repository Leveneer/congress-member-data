import pytest
import os
import logging
from pathlib import Path
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def pytest_addoption(parser):
    parser.addoption(
        "--clean-logs",
        action="store_true",
        default=False,
        help="Clean log files before running tests"
    )

def pytest_sessionstart(session):
    """Set up logging at session start."""
    # Create log directory if needed
    log_file = Path("pytest.log")
    
    # Clean if requested
    if session.config.getoption("--clean-logs") and log_file.exists():
        log_file.unlink()
        print("\nCleared pytest.log")
    
    # Force file creation
    log_file.touch()
    
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        force=True,  # Force reconfiguration
        handlers=[
            logging.FileHandler("pytest.log", mode='a'),
            logging.StreamHandler()
        ]
    )
    
    # Test logging setup
    logging.info("Logging initialized")

@pytest.fixture(autouse=True)
def setup_results_dir():
    """Create and clean up results directory for tests."""
    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)
    yield
    # Clean up test files after tests
    for file in results_dir.glob('test_*.csv'):
        file.unlink()