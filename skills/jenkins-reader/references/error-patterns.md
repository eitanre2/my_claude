# Error Pattern Reference

When analyzing Jenkins console logs, identify ALL errors — not just common patterns.

## Summary Lines

Jobs may contain summary lines indicating overall failure status:
- Pattern: `NOT RERUNNING RSPEC BECAUSE RSPEC FIRST PASS HAD TOO MANY FAILURES (NUMBER - more than the retry threshold: THRESHOLD)`
- This indicates the total number of failures exceeded the retry threshold

## Individual Test Failures

Identified by:
- **Marker line**: Lines containing `Failure/Error:` followed by the failing assertion
- **Error description**: Lines after `Failure/Error:` showing actual vs expected values
- **Stack trace**: File paths with line numbers

Example failure block:
```
Failure/Error: rails_response.status.should == 200

[62]          expected: 200
[62]               got: 403 (using ==)
[62]        # ./spec/requests/requests_helper.rb:828:in `validate_upload_result'
[62]        # ./spec/worker/create_slideshow_spec.rb:267:in `block (4 levels) in <top (required)>'
```

Failed tests may also appear with ANSI color codes.

## Common Error Types

- `ArgumentError`, `NoMethodError`, `NameError`, `StandardError`, `RuntimeError`, `TypeError`, `LoadError`
- HTTP: `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `500 Internal Server Error`
- `undefined method`, `uninitialized constant`
- `Process exited with undefined method` (test initialization failures)
- Expectation failures: `expected.*but.*was`

The analysis scripts detect and categorize ALL error patterns found, not just the ones listed above.
