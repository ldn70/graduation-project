"""Utility helpers for job data normalization and parsing."""

from __future__ import annotations

from datetime import datetime
import re
from typing import Iterable, Optional

from django.utils import timezone


SKILL_SPLIT_PATTERN = re.compile(r"[,，/|;；\s]+")
NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?")


def clean_text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def split_skills(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token.strip().lower() for token in SKILL_SPLIT_PATTERN.split(str(value)) if token.strip()}


def parse_experience_years(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value)
    nums = [float(x) for x in NUMBER_PATTERN.findall(text)]
    if not nums:
        return 0.0
    return sum(nums) / len(nums)


def normalize_education(value: str | None) -> str:
    text = clean_text(value)
    if not text:
        return ""
    mapping = {
        "博士": "博士",
        "硕士": "硕士",
        "研究生": "硕士",
        "本科": "本科",
        "大专": "大专",
        "专科": "大专",
        "不限": "不限",
    }
    for key, normalized in mapping.items():
        if key in text:
            return normalized
    return text


def parse_salary_range_k_month(value: str | None) -> tuple[Optional[float], Optional[float]]:
    """Parse salary text into monthly K range.

    Returns:
        (min_k, max_k)
    """
    text = clean_text(value).lower()
    if not text or "面议" in text or "negotiable" in text:
        return (None, None)

    # Normalize separators and units.
    text = text.replace("～", "-").replace("—", "-").replace("至", "-")
    nums = [float(x) for x in NUMBER_PATTERN.findall(text)]
    if not nums:
        return (None, None)

    factor = 1.0
    if "万" in text:
        factor = 10.0
    elif "k" in text:
        factor = 1.0

    # Yearly salary approximation to monthly.
    if "年" in text and "月" not in text:
        factor = factor / 12.0

    if len(nums) == 1:
        salary = nums[0] * factor
        return (salary, salary)

    left, right = nums[0] * factor, nums[1] * factor
    return (min(left, right), max(left, right))


def parse_publish_time(value: str | None):
    text = clean_text(value)
    if not text:
        return None

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d",
        "%Y.%m.%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(text, fmt)
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        except ValueError:
            continue
    return None


def first_not_empty(values: Iterable[str]) -> str:
    for val in values:
        cleaned = clean_text(val)
        if cleaned:
            return cleaned
    return ""
