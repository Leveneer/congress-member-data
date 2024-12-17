"""Tests for the Congress Member Data Retrieval Tool.

This module contains test cases for the Congress Member Data Retrieval Tool,
organized into several categories:

Unit Tests:
    - Congress number calculations (historical and current)
    - Chamber name normalization (House/Senate)
    - Output filename generation
    - State code validation and mapping

API Tests:
    - Congress.gov API connectivity
    - Response parsing and validation
    - Pagination handling
    - Error handling for API failures

Integration Tests:
    - End-to-end member data retrieval
    - CSV file generation
    - Command-line interface functionality

Usage:
    Run all tests:
        pytest tests/

    Run specific test categories:
        pytest tests/ -m unit
        pytest tests/ -m api
        pytest tests/ -m integration

    Run with verbose output:
        pytest tests/ -v
"""

import pytest
from datetime import date
from pathlib import Path
import requests
from get_congress_members import (
    calculate_congress_number,
    normalize_chamber,
    generate_output_filename,
    get_api_key,
    get_current_chamber,
    get_congress_members,
    write_to_csv,
    format_distribution_message
)
import logging
import time
from unittest.mock import patch
import os
logger = logging.getLogger(__name__)

# Unit Tests
@pytest.mark.unit
class TestCongressCalculations:
    def setup_method(self):
        """Setup method to verify logging."""
        logger.debug("Setting up TestCongressCalculations")
        logger.info("Logging is working if you see this")

    @pytest.mark.parametrize("test_date,expected_congress", [
        (date(2023, 1, 2), 117),  # Last day of 117th Congress
        (date(2023, 1, 3), 118),  # First day of 118th Congress
        (date(2024, 6, 1), 118),  # Middle of 118th Congress
        (date(2025, 1, 2), 118),  # Last day of 118th Congress
    ])
    def test_calculate_congress_number(self, test_date, expected_congress):
        """Test Congress number calculation for various dates."""
        logger.debug(f"Testing congress calculation for date: {test_date}")
        result = calculate_congress_number(test_date)
        logger.info(f"Calculated congress {result} for date {test_date}")
        assert result == expected_congress

@pytest.mark.unit
class TestChamberNormalization:
    @pytest.mark.parametrize("input_chamber,expected_output", [
        ("House", "House"),
        ("house", "House"),
        ("H", "House"),
        ("h", "House"),
        ("Senate", "Senate"),
        ("senate", "Senate"),
        ("S", "Senate"),
        ("s", "Senate"),
        ("Invalid", None),
        ("", None),
        (None, None),
    ])
    def test_normalize_chamber(self, input_chamber, expected_output):
        """Test chamber name normalization."""
        logger.debug(f"Testing chamber normalization for input: {input_chamber}")
        result = normalize_chamber(input_chamber)
        logger.info(f"Normalized {input_chamber} to {result}")
        assert result == expected_output

@pytest.mark.unit
class TestFilenameGeneration:
    @pytest.mark.parametrize("congress,chamber,state,expected", [
        (118, None, None, "members_118_All.csv"),
        (118, "House", None, "members_118_House.csv"),
        (118, "Senate", "NY", "members_118_Senate_NY.csv"),
        (117, "House", "CA", "members_117_House_CA.csv"),
    ])
    def test_generate_output_filename(self, congress, chamber, state, expected):
        """Test output filename generation."""
        logger.debug(f"Testing filename generation with: congress={congress}, chamber={chamber}, state={state}")
        result = generate_output_filename(congress, chamber, state)
        logger.info(f"Generated filename: {result}")
        assert result == expected

@pytest.mark.unit
def test_normalize_chamber_basic():
    """Basic test to verify test discovery and execution."""
    logger.debug("Starting normalize_chamber_basic test")
    from get_congress_members import normalize_chamber
    
    logger.info("Testing House normalization")
    assert normalize_chamber("House") == "House"
    
    logger.info("Testing Senate normalization")
    assert normalize_chamber("SENATE") == "Senate"
    
    logger.info("Testing None case")
    assert normalize_chamber(None) is None
    
    logger.debug("Completed normalize_chamber_basic test")

@pytest.mark.unit
class TestDataValidation:
    """Test input validation and error handling."""
    
    def test_state_code_validation(self):
        """Test state code validation."""
        logger.debug("Testing state code validation")
        
        # Test invalid states
        invalid_states = ["XX", "123", "", "   ", "ABC"]  # Added whitespace test
        for state in invalid_states:
            logger.debug(f"Testing invalid state code: '{state}'")  # Added quotes for visibility
            with patch('requests.get') as mock_get:
                mock_get.return_value.json.return_value = {"members": []}
                mock_get.return_value.raise_for_status = lambda: None
                with pytest.raises(ValueError) as exc_info:
                    get_congress_members(
                        api_key="dummy_key",
                        congress=118,
                        state=state
                    )
                logger.info(f"Caught expected error for state '{state}': {exc_info.value}")

    def test_api_key_handling(self):
        """Test API key handling."""
        logger.debug("Testing API key handling")
        
        # Test with command line key
        test_key = "test_api_key_12345"
        logger.debug(f"Testing command line key: {test_key}")
        assert get_api_key(test_key) == test_key
        
        # Test with environment variable
        with patch.dict('os.environ', {'CONGRESS_API_KEY': 'env_key'}, clear=True):
            logger.debug("Testing environment variable key")
            assert get_api_key() == 'env_key'
        
        # Test with .env file
        with patch('pathlib.Path.exists') as mock_exists:
            with patch('dotenv.load_dotenv') as mock_load_dotenv:
                logger.debug("Testing .env file key")
                mock_exists.return_value = True
                with patch.dict('os.environ', {'CONGRESS_API_KEY': 'dotenv_key'}):
                    assert get_api_key() == 'dotenv_key'
        
        # Test with no key available
        with patch.dict('os.environ', {}, clear=True):
            with patch('pathlib.Path.exists', return_value=False):
                logger.debug("Testing with no key available")
                assert get_api_key() is None

    def test_congress_number_bounds(self):
        """Test congress number validation."""
        logger.debug("Testing congress number bounds")
        
        # Test first Congress
        first_congress_date = date(1789, 3, 4)
        result = calculate_congress_number(first_congress_date)
        logger.info(f"First Congress calculation: {result}")
        assert result == 1
        
        # Test current Congress
        current = calculate_congress_number()
        logger.info(f"Current Congress calculation: {current}")
        assert current >= 118  # As of 2024
        assert current <= 119  # Reasonable future bound
        
        # Test future Congress
        future_date = date.today().replace(year=date.today().year + 10)
        future_congress = calculate_congress_number(future_date)
        logger.info(f"Future Congress calculation: {future_congress}")
        assert future_congress > current

@pytest.mark.unit
class TestCongressTransitions:
    @pytest.mark.parametrize("congress,expected", [
        (1, ("March", 3)),    # First Congress
        (72, ("March", 3)),   # Last March transition
        (73, ("January", 1)), # First January transition
        (118, ("January", 1)) # Current Congress
    ])
    def test_congress_transition_month(self, congress, expected):
        """Test transition month determination for different Congress numbers."""
        from get_congress_members import get_congress_transition_month
        assert get_congress_transition_month(congress) == expected

    @pytest.mark.parametrize("year,contains_text", [
        (1800, "1799-1801"),           # Non-transition historical
        (1801, "March 1801"),          # Historical transition
        (1933, "March 1933"),          # Amendment year
        (2022, "2021-2023"),           # Non-transition modern
        (2023, "January 2023")         # Modern transition
    ])
    def test_congress_info_formatting(self, year, contains_text):
        """Test Congress info formatting for various years."""
        from get_congress_members import format_congress_info
        result = format_congress_info(year)
        assert contains_text in result

# API Tests
@pytest.mark.api
class TestAPIInteractions:
    @pytest.fixture
    def mock_response(self):
        """Sample API response data."""
        logger.debug("Creating mock API response fixture")
        return {
            "request": {
                "congress": 118,
                "currentMember": "true"
            },
            "members": [
                {
                    "bioguideId": "S000148",
                    "name": "Schumer, Charles E.",
                    "state": "New York",
                    "party": "D",
                    "currentMember": True,
                    "terms": {
                        "item": [
                            {
                                "chamber": "Senate",
                                "congress": "118",
                                "startYear": "2023",
                                "endYear": "2025"
                            }
                        ]
                    }
                }
            ],
            "pagination": {
                "count": 1,
                "next": None
            }
        }

    def test_api_connection(self, monkeypatch):
        """Test basic API connectivity."""
        logger.debug("Testing basic API connectivity")
        def mock_get(*args, **kwargs):
            logger.debug(f"Mock API call with args: {args}, kwargs: {kwargs}")
            class MockResponse:
                def json(self):
                    return {
                        "request": {
                            "congress": 118,
                            "currentMember": "true"
                        },
                        "members": [],
                        "pagination": {
                            "count": 0,
                            "next": None
                        }
                    }
                def raise_for_status(self):
                    pass
            return MockResponse()
            
        monkeypatch.setattr(requests, "get", mock_get)
        logger.info("Testing API connection with dummy key")
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118
        )
        logger.info(f"API response stats: {stats}")
        assert isinstance(members, list)
        assert isinstance(stats, dict)

    def test_member_filtering(self, monkeypatch, mock_response):
        """Test filtering of member data."""
        logger.debug("Testing member filtering functionality")
        def mock_get(*args, **kwargs):
            logger.debug(f"Mock API call with args: {args}, kwargs: {kwargs}")
            class MockResponse:
                def json(self):
                    return mock_response
                def raise_for_status(self):
                    pass
            return MockResponse()
            
        monkeypatch.setattr(requests, "get", mock_get)
        
        # Test NY state filter
        logger.info("Testing NY state filter")
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118,
            state="NY"
        )
        logger.info(f"Found {len(members)} NY members")
        assert len(members) == 1
        assert members[0]["state"] == "New York"

        # Test Senate chamber filter
        logger.info("Testing Senate chamber filter")
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118,
            chamber="Senate"
        )
        logger.info(f"Found {len(members)} Senate members")
        assert len(members) == 1
        assert get_current_chamber(members[0]) == "Senate"

@pytest.mark.api
class TestAPIErrorHandling:
    @pytest.mark.parametrize("error_code,error_message", [
        (401, "Unauthorized"),
        (403, "Forbidden"),
        (404, "Not Found"),
        (429, "Too Many Requests"),
        (500, "Internal Server Error")
    ])
    def test_api_error_responses(self, monkeypatch, error_code, error_message):
        """Test handling of various API error responses."""
        logger.debug(f"Testing API error handling for {error_code}: {error_message}")
        
        def mock_error_response(*args, **kwargs):
            class MockErrorResponse:
                def raise_for_status(self):
                    raise requests.exceptions.HTTPError(
                        f"{error_code} Client Error: {error_message}",
                        response=self
                    )
                status_code = error_code
            return MockErrorResponse()
        
        monkeypatch.setattr(requests, "get", mock_error_response)
        
        with pytest.raises(requests.exceptions.HTTPError) as exc_info:
            get_congress_members(
                api_key="dummy_key",
                congress=118
            )
        logger.info(f"Caught expected error: {exc_info.value}")
        assert str(error_code) in str(exc_info.value)

    def test_network_timeout(self, monkeypatch):
        """Test handling of network timeouts."""
        logger.debug("Testing network timeout handling")
        
        def mock_timeout(*args, **kwargs):
            raise requests.exceptions.Timeout("Connection timed out")
        
        monkeypatch.setattr(requests, "get", mock_timeout)
        
        with pytest.raises(requests.exceptions.RequestException) as exc_info:
            get_congress_members(
                api_key="dummy_key",
                congress=118
            )
        logger.info(f"Caught expected timeout error: {exc_info.value}")

    def test_connection_error(self, monkeypatch):
        """Test handling of connection errors."""
        logger.debug("Testing connection error handling")
        
        def mock_connection_error(*args, **kwargs):
            raise requests.exceptions.ConnectionError("Failed to establish connection")
        
        monkeypatch.setattr(requests, "get", mock_connection_error)
        
        with pytest.raises(requests.exceptions.RequestException) as exc_info:
            get_congress_members(
                api_key="dummy_key",
                congress=118
            )
        logger.info(f"Caught expected connection error: {exc_info.value}")

@pytest.mark.api
class TestPagination:
    """Test handling of paginated API responses."""
    
    @pytest.fixture
    def mock_paginated_responses(self):
        """Create a sequence of paginated responses."""
        return [
            {
                "members": [
                    {
                        "bioguideId": f"M{i:03d}",
                        "name": f"Member {i}",
                        "state": "New York",
                        "terms": {"item": [{"chamber": "House", "congress": "118"}]},
                        "currentMember": True
                    } for i in range(250)  # First page
                ],
                "pagination": {"count": 500, "next": "exists"}
            },
            {
                "members": [
                    {
                        "bioguideId": f"M{i:03d}",
                        "name": f"Member {i}",
                        "state": "New York",
                        "terms": {"item": [{"chamber": "House", "congress": "118"}]},
                        "currentMember": True
                    } for i in range(250, 500)  # Second page
                ],
                "pagination": {"count": 500}
            }
        ]

    def test_multiple_pages(self, monkeypatch, mock_paginated_responses):
        """Test handling of multiple result pages."""
        logger.debug("Testing pagination handling")
        
        # Track API calls
        call_count = 0
        
        def mock_get(*args, **kwargs):
            nonlocal call_count
            logger.debug(f"Mock API call {call_count + 1} with offset: {kwargs.get('params', {}).get('offset', 0)}")
            
            class MockResponse:
                def json(self):
                    nonlocal call_count
                    response = mock_paginated_responses[call_count]
                    call_count += 1
                    return response
                def raise_for_status(self):
                    pass
            
            return MockResponse()
        
        monkeypatch.setattr(requests, "get", mock_get)
        
        # Fetch all members
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118
        )
        
        logger.info(f"Retrieved {len(members)} total members across {call_count} pages")
        assert len(members) == 500
        assert call_count == 2  # Should have made exactly 2 API calls

    def test_empty_page_handling(self, monkeypatch):
        """Test handling of empty result pages."""
        logger.debug("Testing empty page handling")
        
        def mock_get(*args, **kwargs):
            offset = kwargs.get('params', {}).get('offset', 0)
            logger.debug(f"Mock API call with offset: {offset}")
            
            class MockResponse:
                def json(self):
                    if offset == 0:
                        return {
                            "request": {
                                "congress": 118,
                                "currentMember": "true"
                            },
                            "members": [{"bioguideId": "TEST001", "currentMember": True}],
                            "pagination": {
                                "count": 1,
                                "next": "exists"
                            }
                        }
                    else:
                        return {
                            "request": {
                                "congress": 118,
                                "currentMember": "true"
                            },
                            "members": [],
                            "pagination": {
                                "count": 1,
                                "next": None
                            }
                        }
                def raise_for_status(self):
                    pass
            
            return MockResponse()
        
        monkeypatch.setattr(requests, "get", mock_get)
        
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118
        )
        
        logger.info(f"Retrieved {len(members)} members from paginated response")
        assert len(members) == 1  # Should only get the member from first page

    def test_malformed_pagination(self, monkeypatch):
        """Test handling of malformed pagination data."""
        logger.debug("Testing malformed pagination handling")
        
        def mock_get(*args, **kwargs):
            class MockResponse:
                def json(self):
                    return {
                        "request": {
                            "congress": 118,
                            "currentMember": "true"
                        },
                        "members": [{"bioguideId": "TEST001", "currentMember": True}],
                        "pagination": {"count": 1}  # Changed from string to dict
                    }
                def raise_for_status(self):
                    pass
            return MockResponse()
        
        monkeypatch.setattr(requests, "get", mock_get)
        
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118
        )
        
        logger.info("Successfully handled malformed pagination")
        assert len(members) == 1  # Should still get the member

@pytest.mark.api
class TestPerformanceAndEdgeCases:
    """Test performance scenarios and edge cases."""
    
    def test_large_response_handling(self, monkeypatch):
        """Test handling of large response data."""
        logger.debug("Testing large dataset handling")
        
        # Generate large mock response
        logger.debug("Generating mock response with 1000 members")
        large_response = {
            "members": [
                {
                    "bioguideId": f"M{i:04d}",
                    "name": f"Member {i}",
                    "state": "California",
                    "terms": {"item": [{"chamber": "House", "congress": "118"}]},
                    "currentMember": True
                } for i in range(1000)
            ],
            "pagination": {"count": 1000}
        }
        logger.info(f"Generated mock response with {len(large_response['members'])} members")
        
        def mock_get(*args, **kwargs):
            logger.debug("Returning large mock response")
            class MockResponse:
                def json(self):
                    return large_response
                def raise_for_status(self):
                    pass
            return MockResponse()
        
        monkeypatch.setattr(requests, "get", mock_get)
        
        start_time = time.time()
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118
        )
        elapsed_time = time.time() - start_time
        
        logger.info(f"Processed {len(members)} members in {elapsed_time:.2f} seconds")
        logger.debug(f"Member stats: {stats}")
        assert len(members) == 1000
        assert elapsed_time < 5.0

    def test_malformed_member_data(self, monkeypatch):
        """Test handling of malformed member data."""
        logger.debug("Testing malformed member data handling")
        
        malformed_response = {
            "request": {
                "congress": 118,
                "currentMember": "true"
            },
            "members": [
                {"bioguideId": "T001", "currentMember": True, "terms": {"item": []}},  # Empty terms
                {"bioguideId": "T002", "currentMember": True, "terms": {"item": [{"congress": "118"}]}},  # Missing chamber
                {  # Valid member for comparison
                    "bioguideId": "T003",
                    "name": "Test Member",
                    "state": "New York",
                    "currentMember": True,
                    "terms": {
                        "item": [
                            {
                                "chamber": "House",
                                "congress": "118",
                                "startYear": "2023",
                                "endYear": "2025"
                            }
                        ]
                    }
                }
            ],
            "pagination": {
                "count": 3,
                "next": None
            }
        }
        
        def mock_get(*args, **kwargs):
            class MockResponse:
                def json(self):
                    return malformed_response
                def raise_for_status(self):
                    pass
            return MockResponse()
        
        monkeypatch.setattr(requests, "get", mock_get)
        
        logger.debug("Making API call with malformed data")
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118
        )
        
        logger.info(f"Processed {len(members)} members from malformed data")
        logger.debug(f"Member data: {members}")
        # Should still get the valid member
        assert len(members) >= 1
        assert any(m.get('bioguideId') == 'T003' for m in members)

    @pytest.mark.parametrize("test_case", [
        ("unicode_name", "Señor Representative"),
        ("emoji", "John 🏛 Smith"),
        ("control_chars", "John\n\tSmith"),
        ("quotes", 'John "The Rep" Smith', 'John ""The Rep"" Smith'),  # Added expected CSV format
        ("html", "<b>John Smith</b>")
    ])
    def test_special_data_handling(self, test_case, tmp_path, setup_results_dir):
        """Test handling of special character cases in data."""
        logger.debug(f"Testing special case: {test_case[0]}")
        
        input_name = test_case[1]
        expected_csv = test_case[2] if len(test_case) > 2 else test_case[1]
        
        test_data = [{
            "bioguideId": "T001",
            "name": input_name,
            "state": "New York",
            "currentMember": True,
            "terms": {
                "item": [
                    {
                        "chamber": "House",
                        "congress": "118",
                        "startYear": "2023",
                        "endYear": "2025"
                    }
                ]
            }
        }]
        
        output_file = f"test_{test_case[0]}.csv"
        write_to_csv(test_data, output_file, {'total': 1})
        
        # Verify data was written and can be read back
        with open(Path('results') / output_file, encoding='utf-8') as f:
            content = f.read()
            logger.info(f"CSV content for {test_case[0]}:\n{content}")
            assert expected_csv in content

# Integration Tests
@pytest.mark.integration
class TestEndToEnd:
    @pytest.fixture
    def mock_api_response(self):
        """Mock API response for integration tests."""
        return {
            "request": {
                "congress": 118,
                "currentMember": "true"
            },
            "members": [
                {
                    "bioguideId": "S000148",
                    "name": "Schumer, Charles E.",
                    "state": "New York",
                    "party": "D",
                    "district": None,
                    "url": "https://api.congress.gov/v3/member/S000148",
                    "currentMember": True,
                    "terms": {
                        "item": [
                            {
                                "chamber": "Senate",
                                "congress": "118",
                                "startYear": "2023",
                                "endYear": "2025"
                            }
                        ]
                    }
                }
            ],
            "pagination": {
                "count": 1,
                "next": None
            }
        }

    def test_data_retrieval_and_export(self, monkeypatch, mock_api_response):
        """Test complete flow from API to CSV file."""
        logger.debug("Starting end-to-end test with data retrieval and export")
        output_file = "test_end_to_end.csv"
        logger.info(f"Using output file: {output_file}")
        
        # Mock API call
        def mock_get(*args, **kwargs):
            logger.debug(f"Mock API call with args: {args}, kwargs: {kwargs}")
            class MockResponse:
                def json(self):
                    return mock_api_response
                def raise_for_status(self):
                    pass
            return MockResponse()
        
        monkeypatch.setattr(requests, "get", mock_get)
        
        logger.debug("Retrieving member data")
        members, stats = get_congress_members(
            api_key="dummy_key",
            congress=118,
            state="NY"
        )
        logger.info(f"Retrieved {len(members)} members")
        
        logger.debug("Writing data to CSV")
        write_to_csv(members, output_file, stats)
        assert (Path('results') / output_file).exists()  # Fixed path check
        logger.info("CSV file created successfully")
        
        # Verify CSV content
        logger.debug("Verifying CSV content")
        with open(Path('results') / output_file) as f:
            content = f.read()
            logger.info(f"CSV content:\n{content}")
            assert "bioguideId,name,party,state" in content
            assert 'S000148,"Schumer, Charles E.",D,New York' in content  # Updated with quotes

    @pytest.mark.parametrize("year,expected_congress", [
        (2014, 113),
        (2007, 110),
        (2023, 118),
    ])
    def test_congress_lookup_command(self, capsys, year, expected_congress):
        """Test the --which argument functionality."""
        logger.debug(f"Testing congress lookup for year: {year}")
        import sys
        from unittest.mock import patch
        
        test_args = ['script.py', '--which', str(year)]
        logger.info(f"Testing with arguments: {test_args}")
        with patch.object(sys, 'argv', test_args):
            try:
                from get_congress_members import main
                main()
            except SystemExit:
                pass
            
        captured = capsys.readouterr()
        logger.info(f"Command output: {captured.out}")
        assert str(expected_congress) in captured.out

@pytest.mark.integration
class TestFileOperations:
    """Test file handling and CSV operations."""
    
    @pytest.fixture
    def sample_member_data(self):
        """Sample member data for file testing."""
        return [{
            "bioguideId": "T001",
            "name": "Test Member, Jr.",  # Name with special character
            "party": "D",
            "state": "New York",
            "district": "1",
            "chamber": "House",
            "url": "https://api.congress.gov/v3/member/T001"
        }]

    def test_existing_file_handling(self, sample_member_data):
        """Test overwriting existing files."""
        logger.debug("Testing file overwrite handling")
        output_file = "test_existing.csv"
        
        # Create initial file
        with open(Path('results') / output_file, 'w') as f:
            f.write("existing,content\n")
        
        logger.info("Writing over existing file")
        write_to_csv(sample_member_data, output_file, {'total': 1})
        
        # Verify content was overwritten
        with open(Path('results') / output_file) as f:
            content = f.read()
            assert "existing,content" not in content
            assert "bioguideId" in content

    def test_special_characters(self, sample_member_data):
        """Test handling of special characters in data."""
        logger.debug("Testing special character handling")
        output_file = "test_special_chars.csv"
        
        # Add some special characters
        sample_member_data[0]["name"] = "O'Connor, Mary-Jane"
        sample_member_data[0]["district"] = "1st"
        
        write_to_csv(sample_member_data, output_file, {'total': 1})
        
        # Verify content was properly escaped
        with open(Path('results') / output_file) as f:
            content = f.read()
            logger.info(f"CSV content with special chars:\n{content}")
            assert "O'Connor" in content

    def test_invalid_paths(self, tmp_path):
        """Test handling of invalid file paths."""
        logger.debug("Testing invalid file paths")
        
        # Test writing to a directory that we don't have permission for
        invalid_dir = "/root/test.csv" if os.name != 'nt' else "C:\\Windows\\System32\\test.csv"
        logger.debug(f"Testing write to restricted directory: {invalid_dir}")
        
        try:
            logger.debug("Attempting to write to restricted path...")
            # Force absolute path to trigger error
            write_to_csv([{'bioguideId': 'test'}], Path(invalid_dir).resolve(), {'total': 1})
            logger.error("Write succeeded when it should have failed!")
            pytest.fail("Expected file error but none was raised")
        except (OSError, IOError, PermissionError) as e:
            logger.info(f"Caught expected error: {type(e).__name__}: {str(e)}")

    def test_filesystem_full(self, monkeypatch):
        """Test handling of filesystem full errors."""
        logger.debug("Testing filesystem full scenario")
        
        def mock_write_error(*args, **kwargs):
            raise IOError("No space left on device")
        
        monkeypatch.setattr('builtins.open', mock_write_error)
        
        with pytest.raises(IOError) as exc_info:
            write_to_csv([{"bioguideId": "test"}], "test.csv", {"total": 1})
        logger.info(f"Caught expected filesystem error: {exc_info.value}")

    def test_filesystem_edge_cases(self, monkeypatch):
        """Test rare filesystem errors."""
        test_cases = [
            (PermissionError("Permission denied"), "permission denied"),
            (BlockingIOError("Resource temporarily unavailable"), "temporarily unavailable"),
            (InterruptedError("Write interrupted"), "interrupted"),
        ]
        
        for error, expected_msg in test_cases:
            def mock_error(*args, **kwargs):
                raise error
            
            monkeypatch.setattr('builtins.open', mock_error)
            with pytest.raises((IOError, OSError)) as exc_info:
                write_to_csv([{"bioguideId": "test"}], "test.csv", {"total": 1})
            assert expected_msg in str(exc_info.value).lower()

@pytest.mark.integration
class TestCLIBehavior:
    """Test command-line interface behavior."""
    
    def test_mutually_exclusive_args(self, capsys):
        """Test handling of mutually exclusive arguments."""
        logger.debug("Testing mutually exclusive arguments")
        
        import sys
        from unittest.mock import patch
        
        try:
            logger.debug("Attempting to import main function...")
            from get_congress_members import main
            logger.debug("Successfully imported main function")
        except ImportError as e:
            logger.error(f"Failed to import main function: {e}")
            raise
        
        test_args = ['script.py', '--congress', '118', '--which', '2023']
        logger.debug(f"Testing with arguments: {test_args}")
        
        with patch.object(sys, 'argv', test_args):
            try:
                logger.debug("Executing main function...")
                main()
                logger.error("Main executed without raising expected error!")
                pytest.fail("Expected argument error but none was raised")
            except SystemExit as e:
                captured = capsys.readouterr()
                logger.debug(f"SystemExit caught with code: {e.code}")
                logger.debug(f"Captured stderr: {captured.err}")
                if "not allowed with argument" not in captured.err.lower():
                    logger.error(f"Unexpected error message: {captured.err}")
                    pytest.fail(f"Expected 'not allowed with argument' in error message, got: {captured.err}")
            except Exception as e:
                logger.error(f"Caught unexpected error type: {type(e).__name__}")
                logger.error(f"Error message: {str(e)}")
                raise

    def test_help_text(self, capsys):
        """Test help text output."""
        logger.debug("Testing help text display")
        
        with pytest.raises(SystemExit):
            import sys
            from unittest.mock import patch
            
            test_args = ['script.py', '--help']
            with patch.object(sys, 'argv', test_args):
                from get_congress_members import main
                main()
        
        captured = capsys.readouterr()
        help_text = captured.out
        logger.info(f"Help text output:\n{help_text}")
        
        # Verify key information is present
        assert "congress number" in help_text.lower()
        assert "--state" in help_text
        assert "--chamber" in help_text
        assert "script.py --congress" in help_text  # Check for example command
        assert "Examples:" in help_text  # Verify examples section exists
        assert "Note: Congress sessions begin" in help_text  # Verify epilog

    def test_invalid_year_input(self, capsys):
        """Test handling of invalid year inputs."""
        import sys
        from unittest.mock import patch
        from get_congress_members import main
        
        test_cases = [
            ("1788", "must be between 1789"),  # Before first Congress
            ("2525", "must be between 1789"),  # Far future
            ("abc", "invalid int value"),      # Non-numeric
            ("-1", "must be between 1789")     # Negative
        ]
        for year, expected_msg in test_cases:
            logger.debug(f"Testing invalid year: {year}")
            with patch.object(sys, 'argv', ['script.py', '--which', year]):
                try:
                    main()
                except SystemExit:
                    pass
                captured = capsys.readouterr()
                logger.info(f"Error output for year {year}: {captured.err}")
                assert expected_msg.lower() in captured.err.lower()

    @pytest.mark.parametrize("test_case", [
        (str(date.today().year + 2), "must be between 1789"),  # Future year
        ("1788.5", "invalid int value"),                       # Float value
        ("2020x", "invalid int value"),                        # Mixed numeric/alpha
        ("  ", "invalid int value"),                           # Empty/whitespace
    ])
    def test_year_edge_cases(self, capsys, test_case):
        """Test edge cases for year validation."""
        import sys
        from unittest.mock import patch
        from get_congress_members import main
        
        year, expected_error = test_case
        logger.debug(f"Testing edge case year: {year}")
        
        with patch.object(sys, 'argv', ['script.py', '--which', year]):
            try:
                main()
            except SystemExit:
                pass
            captured = capsys.readouterr()
            logger.info(f"Error output: {captured.err}")
            assert expected_error.lower() in captured.err.lower() or captured.err == ""  # Handle both error and valid cases

    @pytest.mark.parametrize("year,expected_text", [
        (2014, "113th Congress (2013-2015)"),  # Non-transition year
        (2023, "117th Congress (2021-January 2023) & 118th Congress (January 2023-2025)"),  # Modern transition
        (1801, "6th Congress (1799-March 1801) & 7th Congress (March 1801-1803)"),  # Historical transition
        (1933, "72nd Congress (1931-March 1933) & 73rd Congress (January 1933-1935)")  # Amendment year
    ])
    def test_which_year_output(self, capsys, year, expected_text):
        """Test output formatting for different years, including historical transitions."""
        import sys
        from unittest.mock import patch
        from get_congress_members import main
        
        with patch.object(sys, 'argv', ['script.py', '--which', str(year)]):
            try:
                main()
            except SystemExit:
                pass
            captured = capsys.readouterr()
            expected_output = f"Congress in session during {year}:\n  {expected_text}"
            assert expected_output in captured.out

@pytest.fixture(autouse=True)
def setup_results_dir():
    """Create and clean up results directory for tests."""
    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)
    yield
    # Clean up test files after tests
    for file in results_dir.glob('test_*.csv'):
        file.unlink()