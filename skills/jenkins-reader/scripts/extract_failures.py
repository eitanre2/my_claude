#!/usr/bin/env python3
"""
Extract all Failure/Error occurrences from Jenkins RSpec console output.
Usage: python3 extract_failures.py <console_log_file> [--count-only] [--group-by]

Fast and context-efficient error extraction for quick analysis.
"""

import sys
import re
from collections import defaultdict

def strip_ansi(text):
    """Remove ANSI color codes"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def extract_failures(console_file, count_only=False, group_by=None):
    """
    Extract all Failure/Error: occurrences from console log.

    Args:
        console_file: Path to console log file
        count_only: If True, only return count statistics
        group_by: Group by 'file', 'error_type', or None
    """
    failures = []
    failure_pattern = re.compile(r'^\s*Failure/Error:\s*(.+)$', re.MULTILINE)

    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Strip ANSI codes for cleaner output
    content = strip_ansi(content)

    # Find all Failure/Error lines
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Failure/Error:' in line:
            match = failure_pattern.match(line)
            if match:
                error_line = match.group(1).strip()

                # Extract context: look for spec file in surrounding lines
                spec_file = None
                for j in range(max(0, i-10), i):
                    if '.rb:' in lines[j] and 'spec/' in lines[j]:
                        spec_match = re.search(r'(spec/[^\s:]+\.rb):(\d+)', lines[j])
                        if spec_match:
                            spec_file = spec_match.group(1)
                            break

                # Extract error type from next few lines
                error_type = None
                for j in range(i+1, min(len(lines), i+5)):
                    error_match = re.search(r'(\w+Error|\w+Exception)', lines[j])
                    if error_match:
                        error_type = error_match.group(1)
                        break

                failures.append({
                    'error_line': error_line,
                    'spec_file': spec_file or 'unknown',
                    'error_type': error_type or 'unknown',
                    'line_num': i
                })

    return failures

def print_statistics(failures):
    """Print summary statistics"""
    print("=" * 80)
    print("FAILURE/ERROR SUMMARY")
    print("=" * 80)
    print(f"Total Failure/Error occurrences: {len(failures)}")
    print()

    # Group by error type
    error_types = defaultdict(int)
    for f in failures:
        error_types[f['error_type']] += 1

    print("By Error Type:")
    print("-" * 80)
    for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
        print(f"  {error_type:30} {count:5} ({count/len(failures)*100:.1f}%)")
    print()

    # Group by spec file
    spec_files = defaultdict(int)
    for f in failures:
        spec_files[f['spec_file']] += 1

    print("Top 15 Files with Most Failures:")
    print("-" * 80)
    for spec_file, count in sorted(spec_files.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {count:3}x  {spec_file}")

def print_grouped(failures, group_by):
    """Print failures grouped by specified field"""
    grouped = defaultdict(list)
    for f in failures:
        key = f.get(group_by, 'unknown')
        grouped[key].append(f['error_line'])

    print("=" * 80)
    print(f"FAILURES GROUPED BY {group_by.upper()}")
    print("=" * 80)
    for key, errors in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"\n{key} ({len(errors)} occurrences):")
        print("-" * 80)
        # Show unique error lines only
        unique_errors = list(set(errors))
        for error in unique_errors[:5]:  # Limit to top 5 unique per group
            print(f"  {error[:100]}")  # Truncate long lines

def print_all_failures(failures):
    """Print all failures with context"""
    print("=" * 80)
    print(f"ALL FAILURE/ERROR OCCURRENCES ({len(failures)})")
    print("=" * 80)

    current_file = None
    for i, f in enumerate(failures, 1):
        if f['spec_file'] != current_file:
            current_file = f['spec_file']
            print(f"\n{current_file}:")
            print("-" * 80)

        print(f"{i:4}. [{f['error_type']}] {f['error_line'][:90]}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_failures.py <console_log_file> [--count-only] [--group-by=file|error_type]")
        sys.exit(1)

    console_file = sys.argv[1]
    count_only = '--count-only' in sys.argv
    group_by = None

    for arg in sys.argv[2:]:
        if arg.startswith('--group-by='):
            group_by = arg.split('=')[1]

    # Extract failures
    failures = extract_failures(console_file, count_only, group_by)

    if not failures:
        print("No Failure/Error occurrences found in console log.")
        sys.exit(0)

    # Print based on options
    if count_only:
        print(f"Total Failure/Error occurrences: {len(failures)}")
    elif group_by:
        print_statistics(failures)
        print()
        print_grouped(failures, group_by)
    else:
        print_statistics(failures)
        print()
        print_all_failures(failures)
