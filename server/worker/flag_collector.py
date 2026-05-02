import re


def extract_flags(stdout: str, pattern: str) -> list[str]:
    """Return unique flags found in stdout using the configured regex pattern.

    Order is preserved; duplicates within one run are collapsed.
    Returns an empty list if the pattern is invalid regex.
    """
    try:
        compiled = re.compile(pattern)
    except re.error:
        return []
    return list(dict.fromkeys(compiled.findall(stdout)))
