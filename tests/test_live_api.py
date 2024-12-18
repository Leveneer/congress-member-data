"""Live API tests for Congress Member Data Retrieval Tool.

These tests require a valid Congress.gov API key.
To run: pytest tests/ -m live
"""

import pytest
import os
from datetime import date
from dotenv import load_dotenv
import logging
import requests

logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()

@pytest.mark.live
@pytest.mark.skipif(not os.getenv('CONGRESS_API_KEY'), reason="No API key available")
class TestLiveAPI:
    @pytest.fixture(autouse=True)
    def check_api_available(self):
        """Skip live tests if API is unavailable."""
        try:
            response = requests.get(
                "https://api.congress.gov/v3/member/congress/118",
                params={'api_key': os.getenv('CONGRESS_API_KEY'), 'limit': 1}
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            pytest.skip(f"Congress.gov API unavailable: {e}")

    def test_current_congress_members(self):
        """Test retrieval of current Congress members."""
        from get_congress_members import get_congress_members
        
        # Log without exposing key
        logger.info("Testing with live API key")
        
        members, stats = get_congress_members(
            api_key=os.getenv('CONGRESS_API_KEY'),
            congress=118
        )
        logger.info(f"Retrieved {stats['total']} members")
        assert len(members) > 0
        assert stats['total'] > 0

    def test_ny_delegation(self):
        """Test retrieval of New York delegation."""
        from get_congress_members import get_congress_members
        
        logger.info("Testing NY delegation retrieval")
        members, stats = get_congress_members(
            api_key=os.getenv('CONGRESS_API_KEY'),
            congress=118,
            state="NY"
        )
        logger.info(f"Retrieved {len(members)} NY members")
        assert len(members) >= 28  # 26 House + 2 Senate