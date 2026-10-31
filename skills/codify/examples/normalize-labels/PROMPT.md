# Normalize labels

Accept one JSON object with exactly a `labels` array of strings. Trim Unicode
whitespace from each label, remove duplicate normalized labels, then sort by
Unicode code point. Preserve case, spelling, and empty normalized labels.
Return `{"labels": [...]}`. Reject missing/extra fields, non-arrays, and
non-string labels with exit 1 and no success output. Perform no network calls
or repository writes. The workflow is pure and requires no inference.
