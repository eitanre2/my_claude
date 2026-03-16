#!/usr/bin/env python3
"""
Analyze error patterns in Jenkins console output.
Usage: python3 analyze_error_patterns.py <console_log_file>
"""

import sys
import re
from collections import defaultdict

def analyze_error_patterns(console_file):
    """Find common error patterns in console output"""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    error_patterns = defaultdict(int)

    # Define patterns to search for (generic, not job-specific)
    patterns = {
        'ArgumentError': r'ArgumentError:',
        'NoMethodError': r'NoMethodError:',
        'NameError': r'NameError:',
        'StandardError': r'StandardError:',
        'RuntimeError': r'RuntimeError:',
        'TypeError': r'TypeError:',
        'LoadError': r'LoadError:',
        'HTTP 400': r':bad_request \(400\)',
        'HTTP 401': r':unauthorized \(401\)',
        'HTTP 403': r':forbidden \(403\)',
        'HTTP 404': r':not_found \(404\)',
        'HTTP 500': r':internal_server_error \(500\)',
        'Expectation Failure': r'expected.*but.*was',
        'Undefined Method': r'undefined method',
        'Uninitialized Constant': r'uninitialized constant',
        'Process Exited (undefined method)': r'Process exited with undefined method',
    }

    for error_name, pattern in patterns.items():
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            error_patterns[error_name] = len(matches)

    return error_patterns

def find_error_samples(console_file, pattern, max_samples=3):
    """Find sample occurrences of a specific error pattern"""
    with open(console_file, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    samples = []
    for i, line in enumerate(lines):
        if re.search(pattern, line, re.IGNORECASE):
            # Get context around the error
            context = []
            for j in range(max(0, i-2), min(len(lines), i+3)):
                # Remove ANSI color codes
                clean = re.sub(r'\x1b\[[0-9;]*m', '', lines[j])
                clean = re.sub(r'\[\d+(?:;\d+)*m', '', clean)
                context.append(clean.strip())

            samples.append({
                'line_num': i,
                'context': [c for c in context if c]
            })

            if len(samples) >= max_samples:
                break

    return samples

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_error_patterns.py <console_log_file> [pattern_to_sample]")
        sys.exit(1)

    console_file = sys.argv[1]
    error_patterns = analyze_error_patterns(console_file)

    print("=" * 80)
    print("ERROR PATTERN ANALYSIS")
    print("=" * 80)
    print()

    if error_patterns:
        print("Error patterns found (sorted by frequency):")
        print("-" * 80)
        for error_type, count in sorted(error_patterns.items(), key=lambda x: x[1], reverse=True):
            if count > 0:
                print(f"{error_type:35} {count:6,} occurrences")
    else:
        print("No common error patterns found.")

    # If specific pattern requested, show samples
    if len(sys.argv) > 2:
        pattern = sys.argv[2]
        print()
        print("=" * 80)
        print(f"SAMPLE OCCURRENCES OF: {pattern}")
        print("=" * 80)
        samples = find_error_samples(console_file, pattern, max_samples=3)
        for i, sample in enumerate(samples, 1):
            print(f"\nSample {i} (Line {sample['line_num']}):")
            for line in sample['context'][:5]:
                print(f"  {line}")
