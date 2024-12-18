import pytest
import os
import logging
from pathlib import Path
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "api: mark test as an API test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "live: mark test as requiring live API access")

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

@pytest.fixture
def mock_api_response(monkeypatch):
    """Mock API responses for different Congress numbers"""
    def _mock_response(congress_number):
        def mock_get(*args, **kwargs):
            class MockResponse:
                def json(self):
                    return {
                        "members": [
                            {
                                "bioguideId": "test1",
                                "name": "Test Member",
                                "state": "NY",
                                "party": "D",
                                "terms": {
                                    "item": {  # Single term as dict
                                        "chamber": "Senate",
                                        "congress": str(congress_number)
                                    }
                                },
                                "url": "https://api.congress.gov/v3/member/1"
                            }
                        ],
                        "pagination": {"count": 1, "next": None}
                    }
                def raise_for_status(self):
                    pass
            return MockResponse()
        monkeypatch.setattr("requests.get", mock_get)
    return _mock_response