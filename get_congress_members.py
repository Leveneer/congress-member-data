#!/usr/bin/env python3
"""
Congress Member Data Retrieval Tool

A tool for fetching and exporting congressional member data using the Congress.gov API.
Author: Ben Rossi (https://github.com/brossi)
Repository: https://github.com/Leveneer/congress-member-data

API Endpoints Used:
    - Member endpoint (/v3/member)
      Documentation: https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md

Data Coverage:
    Coverage information for member data can be found at:
    https://www.congress.gov/help/coverage-dates

Rate Limits:
    - 5,000 requests per hour
    - Maximum 250 results per request

Notes:
    - When querying historical congresses, use currentMember=False for complete data
    - For redistricted members, use currentMember=True to get current assignments only

Usage:
    python get_congress_members.py --congress 118 --state NY
    python get_congress_members.py --congress 118 --chamber House
    python get_congress_members.py --congress 118 --state NY --chamber House

Required:
    API key (via .env file, environment variable, or --api-key argument)
    --congress: Congress number (e.g., 118 for current congress)

Optional:
    --chamber: Filter by 'House' or 'Senate'
    --state: Two-letter state code
    --output: CSV output filename

Module Usage:
    # Import and use as a Python module
    from get_congress_members import get_congress_members
    
    # Get member data directly
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
"""

import os
import sys
import argparse
import csv
from typing import Dict, List, Optional
from pathlib import Path
from dotenv import load_dotenv
import requests
from datetime import datetime, date
import textwrap

# TODO: Performance - Consider using requests.Session() for connection pooling and better performance
#       with repeated API calls. See: https://docs.python-requests.org/en/latest/user/advanced/#session-objects

# TODO: Architecture - Consider refactoring to a class-based API client for better encapsulation
#       and easier management of repeated API calls. This would allow for:
#       - Better state management (api_key, session, etc.)
#       - Cleaner interface for multiple API calls
#       - More intuitive error handling and retry logic

# State code to full name mapping
STATE_NAMES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia'
}

# Constants
FIELDS = ['bioguideId', 'name', 'party', 'state', 'district', 'chamber', 'url']

def get_api_key(cmd_line_key: Optional[str] = None) -> Optional[str]:
    """Get API key from command line argument, .env file, or environment variable."""
    if cmd_line_key:
        return cmd_line_key

    env_path = Path('.env')
    if env_path.exists():
        load_dotenv()
    
    return os.getenv('CONGRESS_API_KEY')

def get_current_chamber(member: Dict) -> str:
    """
    Extract the current chamber from a member's terms.
    Normalizes 'House of Representatives' to 'House' for consistency.
    """
    terms = member.get('terms', {}).get('item', [])
    if terms:
        chamber = terms[-1].get('chamber', '')
        # Normalize chamber name
        return 'House' if chamber == 'House of Representatives' else chamber
    return ''

def fetch_congress_members(
    api_key: str,
    congress: int,
    chamber: Optional[str] = None,
    state: Optional[str] = None,
    debug: bool = False
) -> tuple[List[Dict], Dict[str, int]]:
    """
    Fetch member data from Congress.gov API.

    Uses the /v3/member endpoint:
    https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md

    Rate Limits:
        - 5,000 requests per hour
        - 250 results per request (pagination required for full data)

    Args:
        api_key: Congress.gov API key
        congress: Congress number (e.g., 118)
        chamber: Optional chamber filter ('House' or 'Senate')
        state: Optional two-letter state code
        debug: Enable debug output

    Returns:
        Tuple containing:
        - List of member dictionaries
        - Dictionary with distribution statistics
    """
    url = f"https://api.congress.gov/v3/member/congress/{congress}"
    
    # Determine if this is the current Congress
    CURRENT_CONGRESS = 118  # This should be determined dynamically
    is_current_congress = (congress == CURRENT_CONGRESS)
    
    params = {
        'api_key': api_key,
        'format': 'json',
        'limit': 250,  # API maximum
        'currentMember': str(is_current_congress).lower()
    }

    if chamber:
        params['chamber'] = chamber.title()  # Ensure proper case (House or Senate)
        if debug:
            print(f"DEBUG: Filtering for chamber: {chamber}")

    try:
        all_members = []
        offset = 0
        
        while True:
            params['offset'] = offset
            if debug:
                print(f"DEBUG: Fetching with params: {params}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            members = data.get('members', [])
            if debug:
                print(f"DEBUG: Got {len(members)} members in this batch")
            
            if not members:  # No more members to fetch
                break
                
            all_members.extend(members)
            
            # Check if there are more pages
            pagination = data.get('pagination', {})
            if not pagination.get('next'):
                break
                
            offset += params['limit']
        
        if debug:
            print(f"DEBUG: Total members before filtering: {len(all_members)}")
            print(f"DEBUG: Sample member chambers: {[get_current_chamber(m) for m in all_members[:5]]}")
        
        # Apply state filter if specified
        if state:
            state_upper = state.upper()
            state_name = STATE_NAMES.get(state_upper)
            if not state_name:
                raise ValueError(f"Invalid state code: {state}")
            if debug:
                print(f"DEBUG: Filtering for state: {state_name}")
            all_members = [m for m in all_members if m.get('state') == state_name]
            if debug:
                print(f"DEBUG: Members after state filtering: {len(all_members)}")
        
        # Apply chamber filter if API parameter didn't work
        if chamber:
            if debug:
                print(f"DEBUG: Double-checking chamber filter: {chamber}")
            all_members = [m for m in all_members if get_current_chamber(m) == chamber]
            if debug:
                print(f"DEBUG: Members after chamber filtering: {len(all_members)}")
        
        stats = {
            'total': len(all_members),
            'former': 0,
            'redistricted': 0
        }
        
        # Process member statistics
        for member in all_members:
            terms = member.get('terms', {})
            if isinstance(terms, dict):
                terms = terms.get('item', [])
                if isinstance(terms, dict):
                    terms = [terms]
            
            if is_current_congress:
                if not member.get('currentMember', True):
                    stats['former'] += 1
            else:
                # For historical congresses, check if they served the full term
                congress_terms = [t for t in terms if t.get('congress') == str(congress)]
                if any(t.get('endYear') != t.get('startYear', 0) + 2 for t in congress_terms):
                    stats['former'] += 1
            
            # Check for redistricting
            districts = set()
            for term in terms:
                if term.get('congress') == str(congress):
                    if 'district' in term:
                        districts.add(term['district'])
            
            if len(districts) > 1:
                stats['redistricted'] += 1
        
        return all_members, stats

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Congress.gov API: {e}", file=sys.stderr)
        raise

def write_to_csv(members: List[Dict], output_file: str, stats: Dict[str, int]) -> None:
    """Write member data to CSV file."""
    if not members:
        print("No members found to export", file=sys.stderr)
        return

    output_path = Path(output_file)
    
    # If path is absolute and outside results, raise error
    if output_path.is_absolute():
        raise PermissionError(f"Cannot write to absolute path: {output_path}")
    
    # Ensure we're writing to results directory
    results_dir = Path('results')
    results_dir.mkdir(exist_ok=True)
    
    final_path = results_dir / output_path.name
    
    try:
        with open(final_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(members)
            
        print(f"Successfully exported {stats['total']} members to {final_path}")
    except IOError as e:
        raise IOError(f"Error writing to {final_path}: {e}")

def calculate_congress_number(date_obj: date = None) -> int:
    """
    Calculate Congress number for a given date.
    If no date is provided, uses current date.
    """
    if date_obj is None:
        date_obj = date.today()
    
    year = date_obj.year
    base_year = 1789
    base_congress = 1
    
    # Congress terms start in January 3rd of odd-numbered years
    # For even years, use the Congress that started in the previous odd year
    if year % 2 == 0:
        year -= 1
    
    # Check if we're before January 3rd in an odd year
    if year % 2 == 1 and date_obj.month == 1 and date_obj.day < 3:
        year -= 2
    
    congress = base_congress + ((year - base_year) // 2)
    return congress

def get_congress_years(congress: int) -> tuple[int, int]:
    """
    Get the start and end years for a given Congress.
    
    Args:
        congress: Congress number
        
    Returns:
        Tuple of (start_year, end_year)
    """
    base_year = 1789
    base_congress = 1
    
    # Calculate the start year
    start_year = base_year + ((congress - base_congress) * 2)
    return (start_year, start_year + 2)

def generate_output_filename(congress: int, chamber: Optional[str] = None, state: Optional[str] = None) -> str:
    """
    Generate standardized output filename.
    
    Format: members_{congress}_{chamber}_{state}.csv
    where:
    - {congress} is the congress number (e.g., 118)
    - {chamber} is 'House', 'Senate', or 'All' if no chamber specified
    - {state} is the uppercase two-letter state code (if state filter applied)
    
    Examples:
    - members_118_All.csv
    - members_118_House_CA.csv
    - members_118_Senate_NY.csv
    """
    parts = ['members', str(congress)]
    parts.append(chamber if chamber else 'All')
    if state:
        parts.append(state.upper())
    return '_'.join(parts) + '.csv'

def normalize_chamber(chamber: Optional[str]) -> Optional[str]:
    """
    Normalize chamber input to 'House' or 'Senate'.
    
    Accepts variations like:
    - House, house, H, h
    - Senate, senate, S, s
    
    Returns None if input is None or invalid.
    """
    if not chamber:
        return None
        
    chamber = chamber.lower()
    
    if chamber in ['house', 'h']:
        return 'House'
    elif chamber in ['senate', 's']:
        return 'Senate'
    else:
        return None

def get_congress_members(
    api_key: str,
    congress: int,
    chamber: Optional[str] = None,
    state: Optional[str] = None,
    debug: bool = False
) -> tuple[List[Dict], Dict[str, int]]:
    """
    Get congressional member data, either writing to file or returning as a stream.
    
    This function wraps fetch_congress_members to provide a more Pythonic interface
    for other scripts to consume the data directly.
    
    API Documentation:
        Member endpoint: https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/MemberEndpoint.md
        Coverage dates: https://www.congress.gov/help/coverage-dates
    
    Args:
        api_key: Congress.gov API key
        congress: Congress number
        chamber: Optional chamber filter ('House' or 'Senate')
        state: Optional two-letter state code
        debug: Enable debug output
    
    Returns:
        Tuple containing:
        - List of member dictionaries with fields:
          * bioguideId: Unique identifier
          * name: Full name
          * party: Political party
          * state: State represented
          * district: District number (if House member)
          * chamber: 'House' or 'Senate'
          * url: API URL for additional member data
        - Dictionary with distribution statistics:
          * total: Total number of members
          * former: Number of former members
          * redistricted: Number of redistricted members
    """
    # Validate state code
    if state is not None:
        state = state.strip()  # Strip whitespace
        if not state:  # Check if empty after stripping
            raise ValueError("State code cannot be empty")
        if state.upper() not in STATE_NAMES:
            raise ValueError(f"Invalid state code: {state}")
        state = state.upper()  # Normalize to uppercase

    return fetch_congress_members(
        api_key=api_key,
        congress=congress,
        chamber=chamber,
        state=state,
        debug=debug
    )

def format_distribution_message(stats: Dict[str, int]) -> str:
    """Format member distribution statistics for display.
    
    Args:
        stats: Dictionary containing member statistics
            - total: Total number of members
            - former: Number of former members
            - redistricted: Number of redistricted members
    
    Returns:
        Formatted message string
    """
    parts = []
    if stats.get('former', 0):
        parts.append(f"{stats['former']} former")
    if stats.get('redistricted', 0):
        parts.append(f"{stats['redistricted']} redistricted")
    return f"including {', '.join(parts)}" if parts else ""

def main():
    parser = argparse.ArgumentParser(
        description="""Fetch congressional member data.

Examples:
    %(prog)s --congress 118
    %(prog)s --state NY --chamber House
    %(prog)s --which 2023""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Note: Congress sessions begin in January of odd-numbered years.
For more information, visit: https://api.congress.gov/"""
    )
    
    # Create mutually exclusive group
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        '--congress',
        type=int,
        help="Congress number (e.g., 118)"
    )
    group.add_argument(
        '--which',
        type=int,
        help="Look up Congress number for a specific year"
    )
    
    # Other arguments
    parser.add_argument('--chamber', help="Chamber (House/Senate)")
    parser.add_argument('--state', help="Two-letter state code")
    parser.add_argument('--output', help="Output filename")
    parser.add_argument('--api-key', help="Congress.gov API key")
    parser.add_argument('--debug', action='store_true', help="Enable debug output")
    
    args = parser.parse_args()
    
    # Handle year lookup if --which is used
    if args.which:
        year = args.which
        # Add year validation
        if not (1789 <= year <= date.today().year + 1):
            print(f"Error: Invalid year {year}. Must be between 1789 and {date.today().year + 1}",
                  file=sys.stderr)
            sys.exit(1)
        if not isinstance(year, int):
            print(f"Error: Invalid year format. Must be a number.", file=sys.stderr)
            sys.exit(1)
            
        congress = calculate_congress_number(date(year, 1, 3))
        print(f"\nCongress in session during {year}:")
        print(f"  {congress}th Congress ({year-1 if year % 2 == 0 else year}-{year if year % 2 == 0 else year+1})")
        return
    
    # Normalize chamber input
    if args.chamber:
        normalized_chamber = normalize_chamber(args.chamber)
        if normalized_chamber is None:
            print(f"Error: Invalid chamber specification: {args.chamber}. "
                  "Use 'House'/'Senate' or 'H'/'S'.", file=sys.stderr)
            sys.exit(1)
        args.chamber = normalized_chamber

    # Get API key
    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: API key must be provided via --api-key argument, .env file, "
              "or CONGRESS_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    try:
        members, stats = get_congress_members(
            api_key=api_key,
            congress=args.congress,
            chamber=args.chamber,
            state=args.state,
            debug=args.debug
        )
        
        if args.stream:
            # When used as a module, return the data directly
            return members, stats
        else:
            # Generate default output filename if not specified
            if not args.output:
                args.output = generate_output_filename(args.congress, args.chamber, args.state)
            write_to_csv(members, args.output, stats)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

__author__ = "Ben Rossi (https://github.com/brossi)"
__version__ = "1.0.0"