"""Fortlaufende Belegnummern (Kunden, Rechnungen, Lieferanten …)."""


def next_number_from(values, prefix):
    """Nächste Nummer nach dem numerischen Maximum, nicht nach Textsortierung ("SD-002" > "SD-0005" als Text)."""
    nums = []
    for value in values:
        digits = str(value or "").replace(prefix, "", 1).replace("-", "")
        if digits.isdigit():
            nums.append(int(digits))
    return f"{prefix}{max(nums, default=0) + 1:04d}"
