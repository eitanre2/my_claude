#!/usr/bin/env python3
"""
Team Ownership Analysis for Jenkins Console Output

This script analyzes Jenkins console logs and maps failing tests to teams
based on code ownership patterns. It also extracts specific error examples
for each error category.
"""

import sys
import re
import yaml
from pathlib import Path
from collections import defaultdict
from fnmatch import fnmatch

def load_team_ownership(teams_dir):
    """Load all team ownership files"""
    teams = {}
    teams_path = Path(teams_dir)

    for team_file in teams_path.glob("*.yml"):
        with open(team_file, 'r') as f:
            team_data = yaml.safe_load(f)
            team_name = team_data.get('name', team_file.stem)
            teams[team_name] = {
                'pd_service': team_data.get('pd_service_name', 'unknown'),
                'patterns': team_data.get('owned_globs', [])
            }

    return teams

def match_file_to_team(filepath, teams):
    """Match a file path to a team based on ownership patterns"""
    for team_name, team_info in teams.items():
        for pattern in team_info['patterns']:
            # Handle glob patterns
            if fnmatch(filepath, pattern) or fnmatch(f"server/{filepath}", pattern):
                return team_name
    return "unowned"

def extract_failing_tests(console_file):
    """Extract all failing tests with their file paths and error information"""
    failures = []
    failure_to_error = {}  # Map failures to their error messages

    with open(console_file, 'r', errors='ignore') as f:
        content = f.read()

    # First, extract all Failure/Error blocks with context
    # Pattern to find Failure/Error blocks
    error_blocks = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        if 'Failure/Error:' in line:
            # Get surrounding context (up to 50 lines after)
            context_lines = lines[i:min(i+50, len(lines))]
            context = '\n'.join(context_lines)

            # Try to find spec file in previous lines (within 200 lines)
            spec_file = None
            for j in range(max(0, i-200), i):
                if '.rb' in lines[j] and 'spec/' in lines[j]:
                    # Try to extract spec file path
                    match = re.search(r'spec/[^\s\]]+\.rb', lines[j])
                    if match:
                        spec_file = match.group(0)
                        break

            error_blocks.append({
                'line_num': i,
                'context': context,
                'spec_file': spec_file
            })

    # Now extract all "rspec ./spec/..." failure listings
    # These appear in "Failed examples:" sections
    # Remove ANSI color codes first
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    clean_content = ansi_escape.sub('', content)

    # Pattern: "rspec ./spec/path/to/file.rb:line_number # test description"
    # OR "rspec ./spec/path/to/file.rb[1:2:3] # test description"
    failure_pattern = r'rspec \./spec/(.*?\.rb)(?::(\d+)|\[[\d:]+\])(?:\s+#\s+|.*?\]\s+)(.*?)(?=\n|$)'

    for match in re.finditer(failure_pattern, clean_content):
        spec_file = match.group(1)
        line_number = match.group(2) or "?"
        description = match.group(3).strip()

        # Find closest error block for this spec file
        error_type = "Unknown"
        error_message = ""

        # Search for error blocks that might match this failure
        for error_block in error_blocks:
            if error_block['spec_file'] and spec_file in error_block['spec_file']:
                context = error_block['context']

                # Identify error type from context
                if 'NoMethodError' in context:
                    error_type = "NoMethodError"
                    # Extract the actual error message
                    match_err = re.search(r'NoMethodError:([^\n]+)', context)
                    if match_err:
                        error_message = match_err.group(1).strip()[:150]
                elif 'ArgumentError' in context:
                    error_type = "ArgumentError"
                    match_err = re.search(r'ArgumentError:([^\n]+)', context)
                    if match_err:
                        error_message = match_err.group(1).strip()[:150]
                elif 'StandardError' in context:
                    error_type = "StandardError"
                    match_err = re.search(r'StandardError:([^\n]+)', context)
                    if match_err:
                        error_message = match_err.group(1).strip()[:150]
                elif 'RuntimeError' in context:
                    error_type = "RuntimeError"
                elif 'undefined method' in context.lower():
                    error_type = "Undefined Method"
                    match_err = re.search(r'undefined method[^\n]+', context, re.IGNORECASE)
                    if match_err:
                        error_message = match_err.group(0).strip()[:150]
                elif 'expected:' in context and 'got:' in context:
                    error_type = "Expectation Failure"
                    # Extract expected vs got
                    exp_match = re.search(r'expected:\s*(\S+).*?got:\s*(\S+)', context, re.DOTALL)
                    if exp_match:
                        error_message = f"expected: {exp_match.group(1)}, got: {exp_match.group(2)}"
                    # Check for HTTP status codes in expectations
                    if '403' in context:
                        error_type = "HTTP 403"
                    elif '400' in context:
                        error_type = "HTTP 400"
                    elif '404' in context:
                        error_type = "HTTP 404"
                    elif '500' in context:
                        error_type = "HTTP 500"

                break

        failures.append({
            'spec_file': f"spec/{spec_file}",
            'line': line_number,
            'description': description,
            'error_type': error_type,
            'error_message': error_message
        })

    return failures

def categorize_by_team(failures, teams):
    """Categorize failures by team ownership"""
    team_failures = defaultdict(lambda: defaultdict(list))

    for failure in failures:
        team = match_file_to_team(failure['spec_file'], teams)
        error_type = failure['error_type']
        team_failures[team][error_type].append(failure)

    return team_failures

def generate_report(team_failures, teams):
    """Generate comprehensive team ownership report"""
    print("=" * 80)
    print("JENKINS BUILD ANALYSIS - TEAM OWNERSHIP REPORT")
    print("=" * 80)
    print()

    # Calculate totals
    total_failures = sum(sum(len(errors) for errors in team_errors.values())
                         for team_errors in team_failures.values())

    print(f"TOTAL FAILURES: {total_failures}")
    print(f"TEAMS AFFECTED: {len([t for t in team_failures.keys() if t != 'unowned'])}")
    print()

    # Sort teams by number of failures (descending)
    sorted_teams = sorted(team_failures.items(),
                         key=lambda x: sum(len(e) for e in x[1].values()),
                         reverse=True)

    for team_name, error_categories in sorted_teams:
        team_total = sum(len(errors) for errors in error_categories.values())

        print("=" * 80)
        print(f"TEAM: {team_name}")
        if team_name in teams:
            print(f"PagerDuty Service: {teams[team_name]['pd_service']}")
        print(f"Total Failures: {team_total} ({100*team_total/total_failures:.1f}%)")
        print("=" * 80)
        print()

        # Sort error types by frequency
        sorted_errors = sorted(error_categories.items(),
                              key=lambda x: len(x[1]),
                              reverse=True)

        for error_type, failures_list in sorted_errors:
            count = len(failures_list)
            print(f"\n{error_type}: {count} occurrences ({100*count/team_total:.1f}%)")
            print("-" * 80)

            # Show top 5 examples
            print("Top 5 Examples:")
            for i, failure in enumerate(failures_list[:5], 1):
                print(f"\n{i}. {failure['spec_file']}:{failure['line']}")
                print(f"   Test: {failure['description'][:80]}")
                if failure['error_message']:
                    # Clean up error message
                    msg = failure['error_message'].replace('\n', ' ').strip()
                    print(f"   Error: {msg[:150]}")

            if count > 5:
                print(f"\n   ... and {count - 5} more failures of this type")

        print("\n")

def main():
    if len(sys.argv) < 3:
        print("Usage: python3 team_ownership_analysis.py <console_log> <teams_dir>")
        sys.exit(1)

    console_file = sys.argv[1]
    teams_dir = sys.argv[2]

    print("Loading team ownership data...", file=sys.stderr)
    teams = load_team_ownership(teams_dir)
    print(f"Loaded {len(teams)} teams", file=sys.stderr)

    print("Extracting failing tests...", file=sys.stderr)
    failures = extract_failing_tests(console_file)
    print(f"Found {len(failures)} failures", file=sys.stderr)

    print("Categorizing by team...", file=sys.stderr)
    team_failures = categorize_by_team(failures, teams)

    print("Generating report...\n", file=sys.stderr)
    generate_report(team_failures, teams)

if __name__ == '__main__':
    main()
