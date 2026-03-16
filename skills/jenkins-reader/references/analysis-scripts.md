# Jenkins Analysis Scripts

Located in `scripts/` directory. All scripts are generic, work with any Jenkins RSpec console output, require only Python 3 stdlib, and strip ANSI color codes automatically.

## 1. extract_test_summary.py

Extracts overall test statistics and group summaries.

```bash
python3 scripts/extract_test_summary.py <console_log_file>
```

Output: Total examples, failures, pending counts, success rate, per-group summaries, top 10 worst failing groups.

## 2. analyze_error_patterns.py

Identifies and counts common error patterns.

```bash
python3 scripts/analyze_error_patterns.py <console_log_file> [pattern]
```

Patterns detected include: ArgumentError, NoMethodError, NameError, StandardError, RuntimeError, TypeError, LoadError, HTTP status errors (400-500), undefined method, uninitialized constant, RSpec retry threshold messages, and Failure/Error markers.

Optional: Pass a regex pattern as second argument to get sample occurrences with context.

## 3. categorize_failures.py

Groups failures by spec directory/area.

```bash
python3 scripts/categorize_failures.py <console_log_file>
```

Output: Breakdown by area (controllers, models, requests, lib, operations), percentage per area, top files in each area.

## 4. identify_test_groups.py

Maps parallel test groups to their spec files.

```bash
python3 scripts/identify_test_groups.py <console_log_file>
```

Output: Test groups with failure counts, spec files in each group, top 15 worst failing groups with file lists.

## 5. extract_failures.py

Fast extraction of all "Failure/Error:" occurrences.

```bash
python3 scripts/extract_failures.py <console_log_file>
python3 scripts/extract_failures.py <console_log_file> --count-only
python3 scripts/extract_failures.py <console_log_file> --group-by=file
python3 scripts/extract_failures.py <console_log_file> --group-by=error_type
```
