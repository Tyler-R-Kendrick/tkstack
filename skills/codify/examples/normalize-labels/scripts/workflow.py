"""The once-lowered implementation of PROMPT.md; no inference required."""


def execute(payload):
    if set(payload) != {"labels"} or not isinstance(payload["labels"], list):
        raise ValueError("Expected exactly one labels array")
    if any(not isinstance(label, str) for label in payload["labels"]):
        raise ValueError("Every label must be text")
    return {"labels": sorted({label.strip() for label in payload["labels"]})}
