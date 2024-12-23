# Congress Member Data Retrieval Tool

A Python tool for retrieving and analyzing congressional member data from the Congress.gov API. Features historical lookups, filtering by state/chamber, and CSV export capabilities.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Author:** [Ben Rossi](https://github.com/brossi)

## Features

- Fetch member data from any Congress
- Filter by chamber (House or Senate)
- Filter by state
- Export to CSV
- Handles pagination automatically
- Provides member statistics (total, former, redistricted)
- Can be used as a command-line tool or Python module

## API Documentation

This tool uses the following Congress.gov API endpoints:

- [Member Endpoint](https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md) - Primary endpoint for member data
  - Lists current and historical members
  - Provides member details including terms, party affiliation, and contact info
  - Supports filtering by congress, chamber, and state

For the most up-to-date information about:
- API rate limits
- Data coverage
- Response formats
- Available fields

Please refer to the [official Congress.gov API documentation](https://github.com/LibraryOfCongress/api.congress.gov/).

## Prerequisites

- Python 3.7 or higher
- Congress.gov API key ([sign up here](https://api.congress.gov/sign-up/))
  - Rate limit: 5,000 requests per hour
  - See [API documentation](https://github.com/LibraryOfCongress/api.congress.gov/) for usage guidelines

## Setup

1. Install directly from GitHub using pip:
   ```bash
   pip install git+ssh://git@github.com/Leveneer/congress-member-data.git
   ```

   Or clone and install locally:
   ```bash
   git clone https://github.com/Leveneer/congress-member-data.git
   cd congress-member-data
   ```

2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up your API key (choose one method):
   - Create a `.env` file in your working directory (you can copy from template):
     ```bash
     cp .env.template .env  # Then edit .env with your API key
     # Or create directly:
     echo "CONGRESS_API_KEY=your_api_key_here" > .env
     ```
   - Set environment variable:
     ```bash
     # On Windows:
     set CONGRESS_API_KEY=your_api_key_here
     # On macOS/Linux:
     export CONGRESS_API_KEY=your_api_key_here
     ```
   - Use the `--api-key` argument when running the command:
     ```bash
     get-congress-members --api-key your_api_key_here --state NY
     ```

## Usage

### Command Line

Basic usage:
```bash
# Get all members from the current Congress (defaults to current Congress)
get-congress-members

# Get members from a specific Congress
get-congress-members --congress 117  # Previous Congress
```

With filters:
```bash
# Get House members from New York (current Congress)
get-congress-members --state NY --chamber House

# Get all Senate members (current Congress)
get-congress-members --chamber Senate

# Get all members from California (current Congress)
get-congress-members --state CA

# Get Senate members from Texas in the 117th Congress
get-congress-members --congress 117 --state TX --chamber Senate
```

Note: The current Congress (118th) is the default. Use `--congress` only when you need data from a different Congress.

### As a Python Module

```python
from get_congress_members import get_congress_members

# Get member data
members, stats = get_congress_members(
    api_key="your_api_key",
    congress=118,
    state="NY",
    chamber="House"
)

# Process the data
for member in members:
    print(f"{member['name']} - {member['state']}")

# Access statistics
print(f"Total members: {stats['total']}")
print(f"Former members: {stats['former']}")
print(f"Redistricted: {stats['redistricted']}")
```

## Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--congress` | Congress number (e.g., 118) | Current Congress |
| `--which` | Look up Congress number for a specific year | None |
| `--chamber` | Chamber filter (House/Senate) | None (both) |
| `--state` | Two-letter state code | None (all states) |
| `--output` | Output CSV filename | Auto-generated |
| `--api-key` | Congress.gov API key | From env/file |
| `--debug` | Enable debug output | False |

Note: `--congress` and `--which` are mutually exclusive.

### Looking up Congress Numbers

To find out which Congress was in session during a specific year:
```bash
# Look up Congress for a non-transition year
get-congress-members --which 2014
# Output: Congress in session during 2014:
#   113th Congress (2013-2015)

# Look up Congress for a modern transition year
get-congress-members --which 2023
# Output: Congress in session during 2023:
#   117th Congress (2021-January 2023) & 118th Congress (January 2023-2025)

# Look up Congress for a historical transition year
get-congress-members --which 1801
# Output: Congress in session during 1801:
#   6th Congress (1799-March 1801) & 7th Congress (March 1801-1803)
```

Note: Congressional sessions historically began in March (1st-72nd Congress, 1789-1933) and now begin in January (73rd Congress onward, 1933-present) due to the 20th Amendment. For transition years (odd-numbered years), the tool shows both Congresses that served during that year.

## Output

The script creates a `results` directory and saves CSV files there with the following naming convention:
```
members_{congress}_{chamber}_{state}.csv
```

Example filenames:
- `members_118_All.csv`
- `members_118_House_NY.csv`
- `members_118_Senate_CA.csv`

## Data Fields

The CSV output includes the following fields:
- `bioguideId`: Unique identifier
- `name`: Member's full name
- `party`: Political party affiliation (e.g., Democratic, Republican, Independent)
- `state`: State represented
- `district`: District number (House members only)
- `chamber`: House or Senate
- `url`: API URL for additional member data

## Deactivating Virtual Environment

When you're done, deactivate the virtual environment:
```bash
deactivate
```

## Error Handling

The script handles common errors including:
- Invalid API keys
- Network issues
- Invalid state codes
- Invalid chamber specifications
- File writing permissions

Error messages are written to stderr with appropriate exit codes.

## Testing

### Test Categories
- Unit tests (`pytest tests/ -m unit`): No external dependencies
- API tests (`pytest tests/ -m api`): Uses mocked API responses
- Integration tests (`pytest tests/ -m integration`): End-to-end functionality
- Live API tests (`pytest tests/ -m live`): Requires valid API key

### Running Tests
```bash
# Run all tests except live API tests
pytest tests/ -v -s -m "not live"

# Run specific test categories
pytest tests/ -v -s -m unit          # Unit tests only
pytest tests/ -v -s -m api           # API tests only
pytest tests/ -v -s -m integration   # Integration tests
pytest tests/ -v -s -m live         # Live API tests (requires API key)

# Clean logs before running tests
pytest tests/ -v -s --clean-logs             # All tests
pytest tests/ -v -s -m unit --clean-logs     # Unit tests only
```

### Test Configuration
- `tests/pytest.ini`: Main test configuration and markers
- `tests/conftest.py`: Shared test fixtures and setup
- `tests/.coveragerc`: Coverage reporting configuration
- `.env.test`: Test environment variables

### Test Logs
Test execution logs are written to `pytest.log`. You can:
- View existing logs to debug test behavior
- Clean logs before running tests with `--clean-logs`
- Configure logging levels in `pytest.ini`

### Test Coverage

Current test coverage:

| File | Coverage | Details |
|------|----------|---------|
| get_congress_members.py | 92% | 237/259 statements |

Coverage reports can be generated using:
```bash
# For installed package
pytest --cov=get_congress_members --cov-report=term-missing --cov-report=html tests/

# For source code
pytest --cov=. --cov-report=term-missing --cov-report=html --cov-config=tests/.coveragerc tests/
```

This will:
- Show coverage in the console with missing lines
- Generate an HTML report
- Use the configuration from tests/.coveragerc

View the HTML report:
```bash
open coverage_html/index.html
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.