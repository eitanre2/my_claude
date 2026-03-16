#!/usr/bin/env python3
"""
Cluster errors by stack trace patterns and root causes.
Focus on WHERE errors occur rather than specific error messages.
"""

import re
import sys
from collections import defaultdict, Counter

def strip_ansi(text):
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def extract_failures_with_context(console_file):
    """Extract test failures with complete context."""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [strip_ansi(line.rstrip()) for line in f]

    failures = []
    i = 0

    while i < len(lines):
        line_original = lines[i]  # Already stripped of ANSI
        line = line_original

        # Look for "Failure/Error:" marker (case-insensitive)
        if 'Failure/Error' in line:
            failure = {
                'failure_line_num': i,
                'failure_line': line.strip(),
                'error_lines': [],
                'stack_trace': []
            }

            i += 1

            # Collect error message and stack trace
            while i < len(lines):
                line = lines[i]

                # Stack trace line
                if re.match(r'\s*#\s+\./', line):
                    failure['stack_trace'].append(line.strip())
                    i += 1
                # End of this failure
                elif 'Failure/Error' in line or re.match(r'\s*rspec\s+\./', line):
                    break
                # Error message line
                elif line.strip():
                    failure['error_lines'].append(line.strip())
                    i += 1
                else:
                    i += 1

            if failure['stack_trace']:
                failures.append(failure)
            continue

        i += 1

    return failures

def get_root_cause_location(stack_trace):
    """
    Get the root cause location (topmost application code file).
    Skip gem files and test helpers, focus on actual application code.
    """
    for frame in stack_trace:
        # Skip gem files
        if '/gems/' in frame or '/rvm/' in frame:
            continue

        # Extract file path
        match = re.search(r'#\s+\./([^:]+):(\d+)', frame)
        if match:
            file_path = match.group(1)
            line_num = match.group(2)

            # Skip test helper files, focus on actual spec files or app code
            if 'rails_helper' in file_path or 'spec_helper' in file_path:
                continue

            return f"{file_path}:{line_num}"

    # If no specific location found, return the first frame
    if stack_trace:
        match = re.search(r'#\s+\./([^:]+):(\d+)', stack_trace[0])
        if match:
            return f"{match.group(1)}:{match.group(2)}"

    return "unknown"

def get_stack_pattern(stack_trace, depth=3):
    """
    Get a pattern from the stack trace showing the call chain.
    """
    if not stack_trace:
        return "NO_STACK"

    patterns = []
    count = 0

    for frame in stack_trace:
        # Skip gem frames
        if '/gems/' in frame or '/rvm/' in frame:
            continue

        # Extract file and line
        match = re.search(r'#\s+\./([^:]+):(\d+)', frame)
        if match:
            file_path = match.group(1)
            # Get just the filename
            file_name = file_path.split('/')[-1]
            patterns.append(file_name)
            count += 1

            if count >= depth:
                break

    return ' → '.join(patterns) if patterns else "UNKNOWN"

def classify_error(error_lines, failure_line):
    """Classify the error into a category."""
    text = ' '.join(error_lines) + ' ' + failure_line

    # HTTP status codes
    if re.search(r'(?:status|got:|was:)\s*:?(?:forbidden|403)', text, re.I):
        return 'HTTP_403_Forbidden'
    elif re.search(r'(?:status|got:|was:)\s*:?(?:bad.?request|400)', text, re.I):
        return 'HTTP_400_BadRequest'
    elif re.search(r'(?:status|got:|was:)\s*:?(?:not.?found|404)', text, re.I):
        return 'HTTP_404_NotFound'
    elif re.search(r'(?:status|got:|was:)\s*:?(?:internal.?server|500)', text, re.I):
        return 'HTTP_500_InternalServerError'

    # Method errors
    elif re.search(r'undefined method|NoMethodError', text):
        return 'NoMethodError/UndefinedMethod'

    # Argument errors
    elif re.search(r'ArgumentError|wrong number of arguments', text):
        return 'ArgumentError'

    # Mock/Expectation errors
    elif re.search(r'expected:.*time.*received:', text):
        return 'MockExpectationFailure'
    elif re.search(r'expected:.*got:', text):
        return 'ValueExpectationFailure'

    # Standard errors
    elif 'StandardError' in text:
        return 'StandardError'
    elif 'RuntimeError' in text:
        return 'RuntimeError'
    elif 'TypeError' in text:
        return 'TypeError'

    else:
        return 'Other'

def get_error_summary(error_lines, failure_line, max_length=150):
    """Get a short summary of the error."""
    text = failure_line

    # Add key error lines
    for line in error_lines[:3]:
        if 'expected:' in line.lower() or 'got:' in line.lower() or 'error' in line.lower():
            text += ' | ' + line[:80]

    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + '...'

    return text

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cluster_errors_by_stack.py <console_log_file>")
        sys.exit(1)

    console_file = sys.argv[1]

    print("=" * 100)
    print("ERROR CLUSTERING BY STACK TRACE PATTERNS AND ROOT CAUSES")
    print("=" * 100)

    failures = extract_failures_with_context(console_file)
    print(f"\nTotal failures extracted: {len(failures)}\n")

    # Classify all errors
    classified = []
    for f in failures:
        category = classify_error(f['error_lines'], f['failure_line'])
        root_location = get_root_cause_location(f['stack_trace'])
        stack_pattern = get_stack_pattern(f['stack_trace'], depth=5)
        error_summary = get_error_summary(f['error_lines'], f['failure_line'])

        classified.append({
            'category': category,
            'root_location': root_location,
            'stack_pattern': stack_pattern,
            'error_summary': error_summary,
            'full_error': f
        })

    # Group by category
    by_category = defaultdict(list)
    for c in classified:
        by_category[c['category']].append(c)

    # Sort categories by frequency
    sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

    print("=" * 100)
    print("SUMMARY BY ERROR CATEGORY")
    print("=" * 100)

    for category, items in sorted_categories:
        print(f"\n{category}: {len(items)} failures")

    # Detailed analysis for each major category
    print("\n" + "=" * 100)
    print("DETAILED CLUSTERING BY STACK TRACE PATTERN")
    print("=" * 100)

    for category, items in sorted_categories[:10]:  # Top 10 categories
        print(f"\n{'='*100}")
        print(f"CATEGORY: {category} ({len(items)} failures)")
        print(f"{'='*100}")

        # Group by stack pattern
        by_stack = defaultdict(list)
        for item in items:
            by_stack[item['stack_pattern']].append(item)

        sorted_stacks = sorted(by_stack.items(), key=lambda x: len(x[1]), reverse=True)

        print(f"\nFound {len(sorted_stacks)} unique stack patterns")
        print(f"\nTop 15 stack patterns:\n")

        for idx, (stack_pattern, stack_items) in enumerate(sorted_stacks[:15], 1):
            print(f"{idx}. [{len(stack_items)} failures] {stack_pattern}")

            # Count root locations
            locations = Counter(item['root_location'] for item in stack_items)
            top_locations = locations.most_common(5)

            print(f"   Root locations:")
            for loc, count in top_locations:
                print(f"     • {loc} ({count}x)")

            # Show example error
            example = stack_items[0]
            print(f"   Example: {example['error_summary'][:120]}")
            print()

    # Root cause analysis
    print("\n" + "=" * 100)
    print("TOP 30 ROOT CAUSE LOCATIONS (WHERE ERRORS ORIGINATE)")
    print("=" * 100)

    all_locations = Counter(c['root_location'] for c in classified)
    top_locations = all_locations.most_common(30)

    print(f"\nShowing top 30 out of {len(all_locations)} unique locations:\n")

    for idx, (location, count) in enumerate(top_locations, 1):
        # Get error categories for this location
        categories_at_location = Counter(
            c['category'] for c in classified if c['root_location'] == location
        )

        print(f"{idx:2}. [{count:4} failures] {location}")
        print(f"    Error types: {dict(categories_at_location)}")

        # Show example
        examples = [c for c in classified if c['root_location'] == location]
        if examples:
            print(f"    Example: {examples[0]['error_summary'][:100]}")
        print()

    # Stack pattern frequency
    print("\n" + "=" * 100)
    print("TOP 20 MOST COMMON STACK PATTERNS (CALL CHAINS)")
    print("=" * 100)

    all_patterns = Counter(c['stack_pattern'] for c in classified)
    top_patterns = all_patterns.most_common(20)

    print(f"\nShowing top 20 out of {len(all_patterns)} unique patterns:\n")

    for idx, (pattern, count) in enumerate(top_patterns, 1):
        # Get error categories for this pattern
        categories_for_pattern = Counter(
            c['category'] for c in classified if c['stack_pattern'] == pattern
        )

        print(f"{idx:2}. [{count:4} failures] {pattern}")
        print(f"    Error types: {dict(categories_for_pattern)}")
        print()

if __name__ == '__main__':
    main()
