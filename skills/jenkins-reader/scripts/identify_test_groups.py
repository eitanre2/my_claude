#!/usr/bin/env python3
"""
Identify which spec files are in each test group.
Usage: python3 identify_test_groups.py <console_log_file>
"""

import sys
import re
from collections import defaultdict

def identify_test_groups(console_file):
    """Map test groups to their spec files and failure counts"""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # Find what specs are running in each group
    group_specs = {}
    current_group = None

    for i, line in enumerate(lines):
        # Look for group markers with color codes like [0;30;44m[4][0m or just [40]
        group_match = re.search(r'\[(?:\d+;)?\d+(?:;\d+)?m?\[(\d+)\]', line)
        if group_match:
            current_group = group_match.group(1)
            if current_group not in group_specs:
                group_specs[current_group] = {'specs': set(), 'failures': 0, 'examples': 0}

        # Look for rspec file execution
        if 'rspec' in line and '.rb' in line and current_group:
            spec_match = re.search(r'rspec\s+([^\s]+\.rb)', line)
            if spec_match:
                group_specs[current_group]['specs'].add(spec_match.group(1))

        # Look for summary lines for this group
        if current_group and re.search(rf'\[(?:\d+;)?\d+(?:;\d+)?m?\[{current_group}\]', line):
            summary_match = re.search(r'(\d+) examples, (\d+) failures', line)
            if summary_match:
                group_specs[current_group]['examples'] = int(summary_match.group(1))
                group_specs[current_group]['failures'] = int(summary_match.group(2))

    return group_specs

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 identify_test_groups.py <console_log_file>")
        sys.exit(1)

    console_file = sys.argv[1]
    group_specs = identify_test_groups(console_file)

    # Sort groups by failure count
    sorted_groups = sorted(group_specs.items(), key=lambda x: x[1]['failures'], reverse=True)

    print("=" * 80)
    print(f"TEST GROUPS ANALYSIS: {len(group_specs)} groups found")
    print("=" * 80)
    print()

    groups_with_failures = [g for g in group_specs.values() if g['failures'] > 0]
    print(f"Groups with failures: {len(groups_with_failures)}")
    print(f"Clean groups: {len(group_specs) - len(groups_with_failures)}")
    print()

    print("=" * 80)
    print("TOP 15 WORST FAILING GROUPS")
    print("=" * 80)
    print()

    for i, (group_num, data) in enumerate(sorted_groups[:15], 1):
        failure_rate = (data['failures'] / data['examples'] * 100) if data['examples'] > 0 else 0
        print(f"{i:2}. Group {group_num}: {data['failures']} failures / {data['examples']} examples ({failure_rate:.1f}%)")

        if data['specs']:
            spec_list = sorted(data['specs'])
            # Show first few specs
            for spec in spec_list[:5]:
                # Shorten path for readability
                short_path = spec.replace('/home/ubuntu/workspace/Staging2-CI-PR/server/', '')
                short_path = short_path.replace('./spec/', 'spec/')
                print(f"    - {short_path}")
            if len(spec_list) > 5:
                print(f"    ... and {len(spec_list) - 5} more spec files")
        else:
            print(f"    (No spec files identified)")
        print()
