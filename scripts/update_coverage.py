#!/usr/bin/env python3
import re
from pathlib import Path

def parse_coverage_report(report_text: str) -> dict:
    """Parse coverage data from pytest-cov output."""
    coverage_data = {}
    in_coverage_section = False
    
    for line in report_text.splitlines():
        # Look for the coverage report section
        if '---------- coverage:' in line:
            in_coverage_section = True
            continue
        
        if in_coverage_section and line.strip():
            # Skip lines that don't contain file information
            if not any(x in line for x in ['.py', 'TOTAL']):
                continue
                
            # Parse the line containing coverage data
            if '.py' in line:
                parts = re.split(r'\s+', line.strip())
                if len(parts) >= 4:
                    file_name = parts[0]
                    # Skip test files
                    if not file_name.startswith('test_'):
                        try:
                            statements = int(parts[1])
                            missed = int(parts[2])
                            coverage = int(parts[3].rstrip('%'))
                            coverage_data[file_name] = {
                                'statements': statements,
                                'missed': missed,
                                'coverage': coverage
                            }
                        except (ValueError, IndexError):
                            continue
    return coverage_data

def update_readme_coverage(coverage_data: dict):
    """Update the coverage table in README.md."""
    readme_path = Path('README.md')
    if not readme_path.exists():
        print("README.md not found")
        return

    readme_content = readme_path.read_text()
    
    # Find the coverage section
    coverage_pattern = r'(## Test Coverage\n\n.*?\n\n\| File \| Coverage \| Details \|\n\|---.*?\n)(.*?)(\n\n)'
    
    def create_coverage_table(data: dict) -> str:
        """Create the coverage table content."""
        if not data:
            print("No coverage data found")
            return ""
            
        total_stmts = sum(v['statements'] for v in data.values())
        total_missed = sum(v['missed'] for v in data.values())
        total_coverage = round((total_stmts - total_missed) / total_stmts * 100)
        
        table = f"## Test Coverage\n\nCurrent test coverage is {total_coverage}% across all files:\n\n"
        table += "| File | Coverage | Details |\n"
        table += "|------|----------|----------|\n"
        
        for file_name, stats in data.items():
            table += f"| {file_name} | {stats['coverage']}% | {stats['statements'] - stats['missed']}/{stats['statements']} statements |\n"
        
        return table

    # Replace the coverage section
    try:
        new_content = re.sub(
            coverage_pattern,
            lambda m: create_coverage_table(coverage_data) + "\n\n",
            readme_content,
            flags=re.DOTALL
        )
        readme_path.write_text(new_content)
        print("Updated README.md coverage table")
    except Exception as e:
        print(f"Error updating README: {e}")
        print("Coverage data:", coverage_data)

def main():
    """Main function to update coverage information."""
    # Get coverage report
    coverage_output = Path('coverage_report.txt')
    if not coverage_output.exists():
        print("Running coverage report...")
        import subprocess
        result = subprocess.run(
            ['pytest', '--cov=get_congress_members', 
             '--cov-report=term-missing'],
            capture_output=True,
            text=True
        )
        coverage_output.write_text(result.stdout)
    
    # Parse and update
    coverage_data = parse_coverage_report(coverage_output.read_text())
    if coverage_data:
        update_readme_coverage(coverage_data)
    else:
        print("No coverage data found in report")
    coverage_output.unlink(missing_ok=True)

if __name__ == '__main__':
    main()
