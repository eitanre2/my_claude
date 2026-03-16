#!/usr/bin/env python3
"""
Cluster all test failures by error message and stack trace patterns.
"""

import re
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

def strip_ansi(text):
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def extract_failures(console_file):
    """Extract all test failures with their error messages and stack traces."""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [strip_ansi(line.rstrip()) for line in f]

    failures = []
    i = 0
    current_test = None

    while i < len(lines):
        line = lines[i]

        # Look for test description (the line before Failure/Error)
        # Pattern: "rspec ./path/to/spec.rb:123 # description"
        test_match = re.match(r'\s*rspec\s+\./([^\s]+)\s+#\s+(.+)', line)
        if test_match:
            current_test = {
                'file': test_match.group(1),
                'description': test_match.group(2)
            }

        # Look for Failure/Error marker
        if 'Failure/Error:' in line:
            failure = {
                'test_file': current_test['file'] if current_test else 'unknown',
                'test_desc': current_test['description'] if current_test else 'unknown',
                'failure_line': line,
                'error_message': [],
                'stack_trace': []
            }

            i += 1

            # Collect error message lines (lines that explain the error)
            # These typically have specific formatting like "expected:" or error descriptions
            in_error = True
            while i < len(lines) and in_error:
                line = lines[i]

                # Stack trace lines start with # and contain file paths
                if re.match(r'\s*#\s+\./', line):
                    in_error = False
                    continue

                # Empty line might indicate end of error message
                if not line.strip():
                    in_error = False
                    continue

                # Check if we've hit another test marker
                if re.match(r'\s*rspec\s+\./', line) or 'Failure/Error:' in line:
                    in_error = False
                    continue

                # This is part of the error message
                failure['error_message'].append(line.strip())
                i += 1

            # Collect stack trace
            while i < len(lines):
                line = lines[i]

                # Stack trace line pattern: # ./path/to/file.rb:123:in `method_name'
                if re.match(r'\s*#\s+\./', line):
                    failure['stack_trace'].append(line.strip())
                    i += 1
                else:
                    break

            if failure['error_message'] or failure['stack_trace']:
                failures.append(failure)

            continue

        i += 1

    return failures

def normalize_error_message(error_lines):
    """
    Normalize error message for clustering.
    Replace specific values with placeholders to group similar errors.
    """
    text = '\n'.join(error_lines)

    # Replace specific numbers/IDs with placeholders
    text = re.sub(r'\b\d+\b', 'N', text)

    # Replace quoted strings with placeholder
    text = re.sub(r'"[^"]*"', '"STR"', text)
    text = re.sub(r"'[^']*'", "'STR'", text)

    # Replace hex values
    text = re.sub(r'0x[0-9a-fA-F]+', '0xHEX', text)

    # Replace file paths in error messages
    text = re.sub(r'/[^\s:]+', '/PATH', text)

    # Replace URLs
    text = re.sub(r'https?://[^\s]+', 'URL', text)

    return text

def get_stack_pattern(stack_trace):
    """
    Extract pattern from stack trace for clustering.
    Focus on the top few frames and the file/method names.
    """
    if not stack_trace:
        return "NO_STACK"

    # Take top 5 frames
    top_frames = stack_trace[:5]

    pattern_parts = []
    for frame in top_frames:
        # Extract file and method
        match = re.search(r'#\s+\./([^:]+):\d+:in `([^\']+)\'', frame)
        if match:
            file_path = match.group(1)
            method = match.group(2)

            # Simplify file path to just the file name
            file_name = file_path.split('/')[-1]
            pattern_parts.append(f"{file_name}:{method}")
        else:
            # Try alternate pattern without method
            match = re.search(r'#\s+\./([^:]+):\d+', frame)
            if match:
                file_path = match.group(1)
                file_name = file_path.split('/')[-1]
                pattern_parts.append(file_name)

    return ' -> '.join(pattern_parts) if pattern_parts else "UNKNOWN_PATTERN"

def cluster_by_error_message(failures):
    """Cluster failures by normalized error message."""
    clusters = defaultdict(list)

    for failure in failures:
        normalized = normalize_error_message(failure['error_message'])
        clusters[normalized].append(failure)

    return clusters

def cluster_by_stack_pattern(failures):
    """Cluster failures by stack trace pattern."""
    clusters = defaultdict(list)

    for failure in failures:
        pattern = get_stack_pattern(failure['stack_trace'])
        clusters[pattern].append(failure)

    return clusters

def get_primary_error_type(error_lines):
    """Extract the primary error type from error message."""
    text = ' '.join(error_lines)

    # Common error patterns
    if 'NoMethodError' in text or 'undefined method' in text:
        return 'NoMethodError'
    elif 'ArgumentError' in text:
        return 'ArgumentError'
    elif 'expected:' in text and 'got:' in text:
        return 'ExpectationFailure'
    elif 'StandardError' in text:
        return 'StandardError'
    elif 'RuntimeError' in text:
        return 'RuntimeError'
    elif 'TypeError' in text:
        return 'TypeError'
    elif re.search(r'HTTP.*40[03]', text) or re.search(r'\b40[03]\b', text):
        if '403' in text:
            return 'HTTP_403_Forbidden'
        else:
            return 'HTTP_400_BadRequest'
    elif re.search(r'HTTP.*500', text) or re.search(r'\b500\b', text):
        return 'HTTP_500_InternalServerError'
    elif re.search(r'HTTP.*404', text) or re.search(r'\b404\b', text):
        return 'HTTP_404_NotFound'
    else:
        return 'Other'

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cluster_errors.py <console_log_file>")
        sys.exit(1)

    console_file = sys.argv[1]

    print("=" * 80)
    print("EXTRACTING ALL TEST FAILURES")
    print("=" * 80)

    failures = extract_failures(console_file)

    print(f"\nTotal failures extracted: {len(failures)}\n")

    # Cluster by error type first
    print("=" * 80)
    print("CLUSTERING BY ERROR TYPE")
    print("=" * 80)

    type_clusters = defaultdict(list)
    for failure in failures:
        error_type = get_primary_error_type(failure['error_message'])
        type_clusters[error_type].append(failure)

    # Sort by frequency
    sorted_types = sorted(type_clusters.items(), key=lambda x: len(x[1]), reverse=True)

    for error_type, failures_list in sorted_types:
        print(f"\n{error_type}: {len(failures_list)} failures")

    # Now cluster each type by error message
    print("\n" + "=" * 80)
    print("DETAILED CLUSTERING BY ERROR MESSAGE (Top 5 Types)")
    print("=" * 80)

    for error_type, failures_list in sorted_types[:5]:
        print(f"\n{'=' * 80}")
        print(f"ERROR TYPE: {error_type} ({len(failures_list)} failures)")
        print(f"{'=' * 80}")

        msg_clusters = cluster_by_error_message(failures_list)
        sorted_msg_clusters = sorted(msg_clusters.items(), key=lambda x: len(x[1]), reverse=True)

        print(f"\nFound {len(sorted_msg_clusters)} unique error message patterns\n")

        # Show top 10 message patterns for this error type
        for idx, (normalized_msg, cluster_failures) in enumerate(sorted_msg_clusters[:10], 1):
            print(f"\n{'-' * 80}")
            print(f"Pattern #{idx}: {len(cluster_failures)} occurrences")
            print(f"{'-' * 80}")

            # Show the actual error message from first occurrence
            first = cluster_failures[0]
            print("Error Message:")
            for line in first['error_message'][:10]:  # Show first 10 lines
                print(f"  {line}")
            if len(first['error_message']) > 10:
                print(f"  ... ({len(first['error_message']) - 10} more lines)")

            # Show stack trace from first occurrence
            if first['stack_trace']:
                print("\nStack Trace (top 5 frames):")
                for line in first['stack_trace'][:5]:
                    print(f"  {line}")
                if len(first['stack_trace']) > 5:
                    print(f"  ... ({len(first['stack_trace']) - 5} more frames)")

            # Show which test files are affected
            affected_files = defaultdict(int)
            for f in cluster_failures:
                affected_files[f['test_file']] += 1

            print(f"\nAffected test files ({len(affected_files)} unique files):")
            sorted_files = sorted(affected_files.items(), key=lambda x: x[1], reverse=True)
            for file, count in sorted_files[:5]:
                print(f"  {file}: {count} failures")
            if len(sorted_files) > 5:
                print(f"  ... and {len(sorted_files) - 5} more files")

    # Stack trace clustering
    print("\n" + "=" * 80)
    print("CLUSTERING BY STACK TRACE PATTERN (Top 20)")
    print("=" * 80)

    stack_clusters = cluster_by_stack_pattern(failures)
    sorted_stack_clusters = sorted(stack_clusters.items(), key=lambda x: len(x[1]), reverse=True)

    print(f"\nFound {len(sorted_stack_clusters)} unique stack trace patterns\n")

    for idx, (pattern, cluster_failures) in enumerate(sorted_stack_clusters[:20], 1):
        print(f"\n{idx}. Stack Pattern: {pattern}")
        print(f"   Occurrences: {len(cluster_failures)}")

        # Show error types in this stack pattern
        error_types = defaultdict(int)
        for f in cluster_failures:
            error_type = get_primary_error_type(f['error_message'])
            error_types[error_type] += 1

        print(f"   Error types: {dict(error_types)}")

        # Show example
        example = cluster_failures[0]
        print(f"   Example: {example['test_file']}")
        if example['error_message']:
            print(f"   Error: {example['error_message'][0][:100]}")

if __name__ == '__main__':
    main()
