#!/usr/bin/env python3
"""
Cluster errors by stack trace patterns and error messages.
Handles Jenkins console format with timestamps and ANSI codes.
"""

import re
import sys
from collections import defaultdict, Counter

def strip_ansi(text):
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def extract_all_failures(console_file):
    """Extract all test failures with error messages and stack traces."""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [strip_ansi(line.rstrip()) for line in f]

    failures = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Look for "Failure/Error:" marker
        if 'Failure/Error:' in line:
            failure = {
                'failure_line': line,
                'error_message': [],
                'stack_trace': []
            }

            i += 1

            # Collect error message and stack trace
            while i < len(lines):
                line = lines[i]

                # Stack trace line: contains "# ./"
                if '# ./' in line:
                    failure['stack_trace'].append(line)
                    i += 1
                # Another failure started
                elif 'Failure/Error:' in line:
                    break
                # Test marker (end of this failure)
                elif re.search(r'rspec\s+\./', line):
                    break
                # Blank line might end it
                elif not line.strip():
                    # Allow a few blank lines
                    i += 1
                    if i < len(lines) and not lines[i].strip():
                        break
                # Error message line
                else:
                    failure['error_message'].append(line)
                    i += 1

            if failure['stack_trace']:
                failures.append(failure)
            continue

        i += 1

    return failures

def extract_file_from_stack(stack_line):
    """Extract file path from stack trace line."""
    match = re.search(r'#\s+\./([^:]+)', stack_line)
    if match:
        return match.group(1)
    return None

def extract_method_from_stack(stack_line):
    """Extract method from stack trace line."""
    match = re.search(r":in `([^']+)'", stack_line)
    if match:
        return match.group(1)
    return None

def get_root_file(stack_trace):
    """Get the first application file from stack trace (skip gems)."""
    for line in stack_trace:
        file_path = extract_file_from_stack(line)
        if file_path and '/gems/' not in line and '/rvm/' not in line:
            # Skip helper files
            if 'rails_helper' not in file_path and 'spec_helper' not in file_path:
                return file_path

    # Fallback to first frame
    if stack_trace:
        return extract_file_from_stack(stack_trace[0])
    return "unknown"

def get_stack_pattern(stack_trace, depth=3):
    """Get call chain pattern from stack trace."""
    patterns = []
    count = 0

    for line in stack_trace:
        # Skip gem lines
        if '/gems/' in line or '/rvm/' in line:
            continue

        file_path = extract_file_from_stack(line)
        if file_path:
            # Just use filename
            filename = file_path.split('/')[-1]
            patterns.append(filename)
            count += 1
            if count >= depth:
                break

    return ' → '.join(patterns) if patterns else "NO_PATTERN"

def classify_error(error_lines, failure_line):
    """Classify the error type."""
    text = ' '.join(error_lines) + ' ' + failure_line
    text_lower = text.lower()

    # HTTP errors
    if 'status code :forbidden' in text_lower or '(403)' in text or 'got: 403' in text:
        return 'HTTP_403_Forbidden'
    elif '(400)' in text or 'got: 400' in text or 'bad request' in text_lower:
        return 'HTTP_400_BadRequest'
    elif '(404)' in text or 'got: 404' in text or 'not found' in text_lower:
        return 'HTTP_404_NotFound'
    elif '(500)' in text or 'got: 500' in text or 'internal server' in text_lower:
        return 'HTTP_500_InternalServerError'

    # Method errors
    elif 'undefined method' in text_lower or 'nomethoderror' in text_lower:
        return 'NoMethodError/UndefinedMethod'

    # Argument errors
    elif 'argumenterror' in text_lower or 'wrong number of arguments' in text_lower:
        return 'ArgumentError'

    # Mock expectations
    elif 'expected:' in text_lower and 'time' in text_lower and 'received:' in text_lower:
        return 'MockExpectationFailure'

    # Value expectations
    elif 'expected:' in text_lower and 'got:' in text_lower:
        return 'ValueExpectationFailure'

    # Errors
    elif 'standarderror' in text_lower:
        return 'StandardError'
    elif 'runtimeerror' in text_lower:
        return 'RuntimeError'
    elif 'typeerror' in text_lower:
        return 'TypeError'
    elif 'invalidtransformation' in text_lower:
        return 'InvalidTransformation'

    else:
        return 'Other'

def normalize_error_message(error_lines):
    """Normalize error message for clustering."""
    text = ' '.join(error_lines)

    # Replace numbers with N
    text = re.sub(r'\b\d+\b', 'N', text)

    # Replace hex addresses
    text = re.sub(r'0x[0-9a-fA-F]+', '0xHEX', text)

    # Replace strings in quotes
    text = re.sub(r'"[^"]*"', '"STR"', text)
    text = re.sub(r"'[^']*'", "'STR'", text)

    return text

def get_error_summary(error_lines, max_length=150):
    """Get a short summary of the error."""
    for line in error_lines:
        clean = line.strip()
        if clean and not clean.startswith('['):
            if len(clean) > max_length:
                return clean[:max_length] + '...'
            return clean

    if error_lines:
        return error_lines[0][:max_length]
    return "No error message"

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cluster_errors_improved.py <console_log_file>")
        sys.exit(1)

    console_file = sys.argv[1]

    print("=" * 100)
    print("ERROR CLUSTERING ANALYSIS - COMPLETE REPORT")
    print("=" * 100)

    failures = extract_all_failures(console_file)
    print(f"\nTotal failures extracted: {len(failures)}\n")

    if len(failures) == 0:
        print("No failures found!")
        return

    # Classify all errors
    classified = []
    for f in failures:
        category = classify_error(f['error_message'], f['failure_line'])
        root_file = get_root_file(f['stack_trace'])
        stack_pattern = get_stack_pattern(f['stack_trace'], depth=5)
        error_summary = get_error_summary(f['error_message'])
        normalized_msg = normalize_error_message(f['error_message'])

        classified.append({
            'category': category,
            'root_file': root_file,
            'stack_pattern': stack_pattern,
            'error_summary': error_summary,
            'normalized_msg': normalized_msg,
            'raw_failure': f
        })

    # Group by category
    by_category = defaultdict(list)
    for c in classified:
        by_category[c['category']].append(c)

    sorted_categories = sorted(by_category.items(), key=lambda x: len(x[1]), reverse=True)

    print("=" * 100)
    print("1. ERROR CATEGORIES (High-Level Breakdown)")
    print("=" * 100)
    print()

    for category, items in sorted_categories:
        print(f"  {category:40} {len(items):5} failures")

    # Detailed clustering for top categories
    print("\n" + "=" * 100)
    print("2. DETAILED CLUSTERING BY ERROR MESSAGE (Top 5 Categories)")
    print("=" * 100)

    for category, items in sorted_categories[:5]:
        print(f"\n{'='*100}")
        print(f"CATEGORY: {category} ({len(items)} failures)")
        print(f"{'='*100}")

        # Group by normalized message
        by_normalized = defaultdict(list)
        for item in items:
            by_normalized[item['normalized_msg']].append(item)

        sorted_messages = sorted(by_normalized.items(), key=lambda x: len(x[1]), reverse=True)

        print(f"\nFound {len(sorted_messages)} unique error patterns")
        print(f"\nTop 10 error patterns:\n")

        for idx, (normalized, msg_items) in enumerate(sorted_messages[:10], 1):
            print(f"{'-'*100}")
            print(f"Pattern #{idx}: {len(msg_items)} occurrences")
            print(f"{'-'*100}")

            # Show actual error from first occurrence
            example = msg_items[0]
            print(f"Error: {example['error_summary']}")
            print()

            # Show top files affected
            files = Counter(item['root_file'] for item in msg_items)
            print(f"Top files affected:")
            for file, count in files.most_common(5):
                print(f"  • {file} ({count}x)")
            print()

            # Show stack pattern
            patterns = Counter(item['stack_pattern'] for item in msg_items)
            print(f"Top stack patterns:")
            for pattern, count in patterns.most_common(3):
                print(f"  • {pattern} ({count}x)")
            print()

    # Root file analysis
    print("\n" + "=" * 100)
    print("3. TOP 30 ROOT CAUSE FILES (Where Errors Originate)")
    print("=" * 100)
    print()

    all_files = Counter(c['root_file'] for c in classified)
    top_files = all_files.most_common(30)

    for idx, (file_path, count) in enumerate(top_files, 1):
        # Get error categories for this file
        categories = Counter(c['category'] for c in classified if c['root_file'] == file_path)

        print(f"{idx:2}. [{count:4} failures] {file_path}")

        # Show top 3 error types
        top_cats = categories.most_common(3)
        cat_str = ', '.join([f"{cat}({cnt})" for cat, cnt in top_cats])
        print(f"    Types: {cat_str}")

        # Show example
        examples = [c for c in classified if c['root_file'] == file_path]
        if examples:
            print(f"    Example: {examples[0]['error_summary'][:80]}")
        print()

    # Stack pattern frequency
    print("\n" + "=" * 100)
    print("4. TOP 20 MOST COMMON STACK PATTERNS (Call Chains)")
    print("=" * 100)
    print()

    all_patterns = Counter(c['stack_pattern'] for c in classified)
    top_patterns = all_patterns.most_common(20)

    for idx, (pattern, count) in enumerate(top_patterns, 1):
        categories = Counter(c['category'] for c in classified if c['stack_pattern'] == pattern)

        print(f"{idx:2}. [{count:4} failures] {pattern}")

        # Show error types
        top_cats = categories.most_common(3)
        cat_str = ', '.join([f"{cat}({cnt})" for cat, cnt in top_cats])
        print(f"    Types: {cat_str}")
        print()

if __name__ == '__main__':
    main()
