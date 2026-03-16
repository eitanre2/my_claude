#!/usr/bin/env python3
"""
Categorize test failures by spec area/module.
Usage: python3 categorize_failures.py <console_log_file>
"""

import sys
import re
from collections import defaultdict

def categorize_failures(console_file):
    """Categorize failed tests by spec directory"""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find all failed test sections
    failed_sections = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        if 'Failed examples:' in line:
            # Extract the next 100 lines to capture failed test paths
            section_lines = []
            j = i + 1
            while j < len(lines) and j < i + 100:
                next_line = lines[j]
                # Stop if we hit another test group marker or summary
                if 'examples,' in next_line and 'failures' in next_line:
                    break
                if next_line.strip() and 'rspec' in next_line:
                    section_lines.append(next_line.strip())
                j += 1
            failed_sections.extend(section_lines)

    # Parse test failures and categorize by area
    test_failures = []
    for line in failed_sections:
        # Extract spec file path
        match = re.search(r'rspec\s+([^\s]+)', line)
        if match:
            spec_path = match.group(1)
            test_failures.append({
                'full_line': line,
                'spec_path': spec_path
            })

    # Categorize by area/module
    categories = defaultdict(list)

    for test in test_failures:
        spec_path = test['spec_path']

        # Extract main area from path
        if '/spec/' in spec_path:
            parts = spec_path.split('/spec/')[-1].split('/')
            if len(parts) > 1:
                area = parts[0]
            else:
                area = 'root'
        else:
            area = 'unknown'

        categories[area].append(test)

    return categories, test_failures

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 categorize_failures.py <console_log_file>")
        sys.exit(1)

    console_file = sys.argv[1]
    categories, all_failures = categorize_failures(console_file)

    print("=" * 80)
    print(f"CATEGORIZED FAILURES: {len(all_failures)} total failed tests")
    print("=" * 80)
    print()
    print("BREAKDOWN BY AREA:")
    print("-" * 80)

    for area in sorted(categories.keys(), key=lambda x: len(categories[x]), reverse=True):
        count = len(categories[area])
        percentage = (count / len(all_failures) * 100) if all_failures else 0
        print(f"{area:20} {count:5} failures ({percentage:5.1f}%)")

    print()
    print("=" * 80)
    print("TOP AREAS WITH FAILURES:")
    print("=" * 80)

    for area in sorted(categories.keys(), key=lambda x: len(categories[x]), reverse=True)[:5]:
        print(f"\n{area.upper()}: {len(categories[area])} failures")

        # Group by specific file
        files = defaultdict(int)
        for test in categories[area]:
            spec_file = test['spec_path'].split('/')[-1].split(':')[0]
            files[spec_file] += 1

        print("  Top files:")
        for file in sorted(files.keys(), key=lambda x: files[x], reverse=True)[:5]:
            print(f"    {file}: {files[file]} failures")
