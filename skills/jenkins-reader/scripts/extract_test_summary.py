#!/usr/bin/env python3
"""
Extract test summary from Jenkins console output.
Usage: python3 extract_test_summary.py <console_log_file>
"""

import sys
import re

def extract_test_summary(console_file):
    """Extract final test summary and per-group summaries"""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Find final summary
    final_summary = None
    lines = content.split('\n')
    for line in reversed(lines):
        if 'examples,' in line and 'failures' in line and 'pendings' in line:
            match = re.search(r'(\d+) examples, (\d+) failures, (\d+) pendings', line)
            if match:
                final_summary = {
                    'total_examples': int(match.group(1)),
                    'total_failures': int(match.group(2)),
                    'total_pending': int(match.group(3))
                }
                break

    # Find test group summaries
    test_groups = []
    for line in content.split('\n'):
        if re.search(r'\[\d+\].*examples,.*failures', line):
            match = re.search(r'\[(\d+)\].*?(\d+) examples, (\d+) failures', line)
            if match:
                group_num = match.group(1)
                examples = int(match.group(2))
                failures = int(match.group(3))
                test_groups.append({
                    'group': group_num,
                    'examples': examples,
                    'failures': failures,
                    'failure_rate': (failures / examples * 100) if examples > 0 else 0
                })

    return final_summary, test_groups

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 extract_test_summary.py <console_log_file>")
        sys.exit(1)

    console_file = sys.argv[1]
    final, groups = extract_test_summary(console_file)

    if final:
        print("=" * 80)
        print("FINAL TEST SUMMARY")
        print("=" * 80)
        print(f"Total Examples: {final['total_examples']:,}")
        print(f"Total Failures: {final['total_failures']:,}")
        print(f"Total Pending: {final['total_pending']:,}")
        passed = final['total_examples'] - final['total_failures'] - final['total_pending']
        success_rate = (passed / final['total_examples'] * 100) if final['total_examples'] > 0 else 0
        print(f"Passed: {passed:,}")
        print(f"Success Rate: {success_rate:.1f}%")
        print()

    if groups:
        print("=" * 80)
        print(f"TEST GROUPS: {len(groups)} groups")
        print("=" * 80)
        groups_with_failures = [g for g in groups if g['failures'] > 0]
        print(f"Groups with failures: {len(groups_with_failures)}")
        print(f"Clean groups: {len(groups) - len(groups_with_failures)}")
        print()

        # Top 10 worst
        sorted_groups = sorted(groups, key=lambda x: x['failures'], reverse=True)
        print("TOP 10 WORST FAILING GROUPS:")
        print("-" * 80)
        for i, group in enumerate(sorted_groups[:10], 1):
            print(f"{i:2}. Group [{group['group']:2}]: {group['failures']:3} failures / "
                  f"{group['examples']:4} examples ({group['failure_rate']:.1f}%)")
