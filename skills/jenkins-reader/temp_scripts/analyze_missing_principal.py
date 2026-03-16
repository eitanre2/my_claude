#!/usr/bin/env python3
"""
Extract all RSpec failures with 'ArgumentError: missing principal type'
and group them by spec file with full stack traces.
"""

import re
import sys
from collections import defaultdict

def extract_missing_principal_failures(console_file):
    """Extract all failures with 'missing principal type' error."""

    with open(console_file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # Pattern to match RSpec failure blocks
    # Looks for: numbered failure, then captures until next numbered failure or finished line
    failure_pattern = r'\[\d{4}-\d{2}-\d{2}T[\d:\.]+Z\] \[(\d+)\]\s+(\d+)\) (.+?)(?=\[\d{4}-\d{2}-\d{2}T[\d:\.]+Z\] \[\d+\]\s+(?:\d+\)|Finished in|Randomized with seed))'

    failures = []
    for match in re.finditer(failure_pattern, content, re.DOTALL):
        group_num = match.group(1)
        failure_num = match.group(2)
        failure_text = match.group(3)

        # Check if this failure contains "missing principal type"
        if 'missing principal type' in failure_text:
            failures.append({
                'group': group_num,
                'number': failure_num,
                'text': failure_text
            })

    return failures

def parse_failure(failure_text):
    """Parse a failure to extract test name, spec file, and stack trace."""
    lines = failure_text.strip().split('\n')

    # First line is the test description
    test_desc = lines[0].strip() if lines else ''

    # Find the spec file from stack trace (lines starting with # ./spec/)
    spec_file = None
    stack_lines = []

    for line in lines:
        # Remove timestamp prefix if present
        clean_line = re.sub(r'^\[\d{4}-\d{2}-\d{2}T[\d:\.]+Z\] \[\d+\]\s*', '', line)

        # Look for stack trace lines
        if clean_line.strip().startswith('# ./spec/'):
            if spec_file is None:
                # First spec file in stack is where the test is defined
                match = re.search(r'# \./spec/([^:]+)', clean_line)
                if match:
                    spec_file = match.group(1)
            stack_lines.append(clean_line.strip())
        elif clean_line.strip().startswith('# ./lib/'):
            stack_lines.append(clean_line.strip())

    return {
        'test_desc': test_desc,
        'spec_file': spec_file or 'UNKNOWN',
        'stack_lines': stack_lines,
        'full_text': failure_text
    }

def group_by_spec_file(failures):
    """Group failures by spec file."""
    grouped = defaultdict(list)

    for failure in failures:
        parsed = parse_failure(failure['text'])
        grouped[parsed['spec_file']].append({
            'group': failure['group'],
            'number': failure['number'],
            'test_desc': parsed['test_desc'],
            'stack_lines': parsed['stack_lines'],
            'full_text': failure['text']
        })

    return grouped

def print_report(grouped_failures):
    """Print a formatted report of failures grouped by spec file."""

    total_failures = sum(len(failures) for failures in grouped_failures.values())

    print("=" * 80)
    print(f"ARGUMENTERROR: MISSING PRINCIPAL TYPE - FAILURE REPORT")
    print("=" * 80)
    print(f"\nTotal failures with this error: {total_failures}")
    print(f"Unique spec files affected: {len(grouped_failures)}")
    print("\n")

    # Sort by number of failures (descending)
    sorted_files = sorted(grouped_failures.items(), key=lambda x: len(x[1]), reverse=True)

    for spec_file, failures in sorted_files:
        print("=" * 80)
        print(f"SPEC FILE: {spec_file}")
        print(f"Failures: {len(failures)}")
        print("=" * 80)
        print()

        for idx, failure in enumerate(failures, 1):
            print(f"--- Failure #{idx} (Group {failure['group']}, Test #{failure['number']}) ---")
            print(f"Test: {failure['test_desc']}")
            print()

            # Print stack trace focusing on the error flow
            print("Stack Trace (from spec to permission enforcer):")
            for stack_line in failure['stack_lines']:
                print(f"  {stack_line}")

            print()

            # Print excerpt showing the error
            lines = failure['full_text'].split('\n')
            error_section = []
            capture = False
            for line in lines:
                clean = re.sub(r'^\[\d{4}-\d{2}-\d{2}T[\d:\.]+Z\] \[\d+\]\s*', '', line)
                if 'Failure/Error:' in clean or 'ArgumentError:' in clean:
                    capture = True
                if capture:
                    error_section.append(clean)
                    if clean.strip().startswith('# ./') and 'permission' in clean.lower():
                        break

            if error_section:
                print("Error Details:")
                for line in error_section[:10]:  # Limit to first 10 lines
                    print(f"  {line}")

            print()
            print("-" * 80)
            print()

    print("\n")
    print("=" * 80)
    print("SUMMARY BY SPEC FILE")
    print("=" * 80)
    for spec_file, failures in sorted_files:
        print(f"{len(failures):4d} failures - {spec_file}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 analyze_missing_principal.py <console_log_file>")
        sys.exit(1)

    console_file = sys.argv[1]

    print("Extracting failures with 'missing principal type' error...")
    failures = extract_missing_principal_failures(console_file)

    print(f"Found {len(failures)} failures with this error.")
    print("Parsing and grouping by spec file...")

    grouped = group_by_spec_file(failures)

    print_report(grouped)
