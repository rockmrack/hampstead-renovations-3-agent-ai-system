"""
Hampstead Renovations - Shared Utilities
=========================================

Common validation, formatting, and helper functions used across all agents.
"""

import re
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Optional, TypedDict
from zoneinfo import ZoneInfo

# London timezone
LONDON_TZ = ZoneInfo("Europe/London")


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================


class ValidationResult(TypedDict):
    valid: bool
    value: Optional[str]
    error: Optional[str]
    normalized: Optional[str]


class PostcodeInfo(TypedDict):
    original: str
    normalized: str
    outward: str
    inward: str
    area: str
    district: str
    in_service_area: bool
    is_premium_area: bool
    area_name: Optional[str]


# =============================================================================
# UK POSTCODE VALIDATION & PARSING
# =============================================================================

# UK postcode regex pattern (handles all valid formats)
UK_POSTCODE_PATTERN = re.compile(
    r"^([A-Z]{1,2})(\d{1,2}[A-Z]?)\s*(\d)([A-Z]{2})$",
    re.IGNORECASE,
)

# Service areas for Hampstead Renovations
PRIMARY_SERVICE_AREAS = {"NW3", "NW6", "NW11"}
SECONDARY_SERVICE_AREAS = {"NW2", "NW8", "N6", "N2", "N10"}
TERTIARY_SERVICE_AREAS = {"NW1", "NW5", "NW10", "N1", "N3", "N7"}
ALL_SERVICE_AREAS = PRIMARY_SERVICE_AREAS | SECONDARY_SERVICE_AREAS | TERTIARY_SERVICE_AREAS

# Premium areas with price multipliers
PREMIUM_AREAS = {
    "NW3": 1.15,  # Hampstead
    "NW11": 1.10,  # Hampstead Garden Suburb
    "N6": 1.08,  # Highgate
    "NW6": 1.05,  # West Hampstead
}

# Area name mapping
AREA_NAMES = {
    "NW3": "Hampstead",
    "NW6": "West Hampstead / Kilburn",
    "NW11": "Hampstead Garden Suburb",
    "NW2": "Cricklewood / Dollis Hill",
    "NW8": "St John's Wood",
    "N6": "Highgate",
    "N2": "East Finchley",
    "N10": "Muswell Hill",
    "NW1": "Camden Town",
    "NW5": "Kentish Town",
    "N1": "Islington",
    "N3": "Finchley",
    "N7": "Holloway",
}


def validate_uk_postcode(postcode: str) -> ValidationResult:
    """
    Validate and normalize a UK postcode.

    Args:
        postcode: Raw postcode string

    Returns:
        ValidationResult with normalized postcode or error
    """
    if not postcode:
        return {
            "valid": False,
            "value": None,
            "error": "Postcode is required",
            "normalized": None,
        }

    # Clean and uppercase
    cleaned = postcode.strip().upper().replace(" ", "")

    # Check minimum length
    if len(cleaned) < 5 or len(cleaned) > 7:
        return {
            "valid": False,
            "value": postcode,
            "error": "Invalid postcode length",
            "normalized": None,
        }

    # Try to match pattern
    match = UK_POSTCODE_PATTERN.match(cleaned)
    if not match:
        return {
            "valid": False,
            "value": postcode,
            "error": "Invalid postcode format",
            "normalized": None,
        }

    # Extract components and format properly
    area, district, sector, unit = match.groups()
    normalized = f"{area.upper()}{district.upper()} {sector}{unit.upper()}"

    return {
        "valid": True,
        "value": postcode,
        "error": None,
        "normalized": normalized,
    }


def parse_postcode(postcode: str) -> Optional[PostcodeInfo]:
    """
    Parse a UK postcode and extract detailed information.

    Args:
        postcode: UK postcode string

    Returns:
        PostcodeInfo dict or None if invalid
    """
    validation = validate_uk_postcode(postcode)
    if not validation["valid"]:
        return None

    normalized = validation["normalized"]
    parts = normalized.split()
    outward = parts[0]
    inward = parts[1] if len(parts) > 1 else ""

    # Extract area (letters only) and district (area + numbers)
    area_match = re.match(r"([A-Z]+)", outward)
    area = area_match.group(1) if area_match else ""

    district_match = re.match(r"([A-Z]+\d+)", outward)
    district = district_match.group(1) if district_match else outward

    return {
        "original": postcode,
        "normalized": normalized,
        "outward": outward,
        "inward": inward,
        "area": area,
        "district": district,
        "in_service_area": district in ALL_SERVICE_AREAS,
        "is_premium_area": district in PREMIUM_AREAS,
        "area_name": AREA_NAMES.get(district),
    }


def get_service_area_tier(postcode: str) -> Optional[str]:
    """
    Determine which service tier a postcode falls into.

    Returns: "primary", "secondary", "tertiary", or None if outside service area
    """
    info = parse_postcode(postcode)
    if not info:
        return None

    district = info["district"]
    if district in PRIMARY_SERVICE_AREAS:
        return "primary"
    elif district in SECONDARY_SERVICE_AREAS:
        return "secondary"
    elif district in TERTIARY_SERVICE_AREAS:
        return "tertiary"
    return None


def get_location_multiplier(postcode: str) -> Decimal:
    """
    Get the price multiplier for a location.

    Premium areas command higher prices due to:
    - Higher property values
    - More complex planning requirements
    - Conservation area considerations
    """
    info = parse_postcode(postcode)
    if not info:
        return Decimal("1.0")

    district = info["district"]
    multiplier = PREMIUM_AREAS.get(district, 1.0)
    return Decimal(str(multiplier))


# =============================================================================
# UK PHONE NUMBER VALIDATION
# =============================================================================

# UK phone patterns
UK_MOBILE_PATTERN = re.compile(r"^(?:\+44|0)7\d{9}$")
UK_LANDLINE_PATTERN = re.compile(r"^(?:\+44|0)[1-9]\d{8,9}$")


def validate_uk_phone(phone: str) -> ValidationResult:
    """
    Validate and normalize a UK phone number.

    Args:
        phone: Raw phone number string

    Returns:
        ValidationResult with E.164 format or error
    """
    if not phone:
        return {
            "valid": False,
            "value": None,
            "error": "Phone number is required",
            "normalized": None,
        }

    # Remove all non-digits except leading +
    cleaned = re.sub(r"[^\d+]", "", phone.strip())

    # Remove leading + for processing
    has_plus = cleaned.startswith("+")
    digits_only = cleaned.lstrip("+")

    # Handle different formats
    if digits_only.startswith("44"):
        # Already has country code
        e164 = f"+{digits_only}"
        national = f"0{digits_only[2:]}"
    elif digits_only.startswith("0"):
        # UK national format
        e164 = f"+44{digits_only[1:]}"
        national = digits_only
    else:
        # Assume it's missing the leading 0
        e164 = f"+44{digits_only}"
        national = f"0{digits_only}"

    # Validate against patterns
    if UK_MOBILE_PATTERN.match(national):
        return {
            "valid": True,
            "value": phone,
            "error": None,
            "normalized": e164,
        }
    elif UK_LANDLINE_PATTERN.match(national):
        return {
            "valid": True,
            "value": phone,
            "error": None,
            "normalized": e164,
        }

    return {
        "valid": False,
        "value": phone,
        "error": "Invalid UK phone number format",
        "normalized": None,
    }


def format_phone_display(phone: str) -> str:
    """
    Format a phone number for display (UK format with spaces).

    Example: +447700900123 -> 07700 900 123
    """
    validation = validate_uk_phone(phone)
    if not validation["valid"] or not validation["normalized"]:
        return phone

    e164 = validation["normalized"]

    # Convert to national format with spaces
    if e164.startswith("+44"):
        national = f"0{e164[3:]}"
        if len(national) == 11:
            # Mobile: 07XXX XXX XXX
            return f"{national[:5]} {national[5:8]} {national[8:]}"
        elif len(national) == 10:
            # Landline: 0XX XXXX XXXX
            return f"{national[:3]} {national[3:7]} {national[7:]}"

    return phone


# =============================================================================
# EMAIL VALIDATION
# =============================================================================

EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


def validate_email(email: str) -> ValidationResult:
    """
    Validate an email address.

    Args:
        email: Email address string

    Returns:
        ValidationResult
    """
    if not email:
        return {
            "valid": False,
            "value": None,
            "error": "Email is required",
            "normalized": None,
        }

    cleaned = email.strip().lower()

    if not EMAIL_PATTERN.match(cleaned):
        return {
            "valid": False,
            "value": email,
            "error": "Invalid email format",
            "normalized": None,
        }

    return {
        "valid": True,
        "value": email,
        "error": None,
        "normalized": cleaned,
    }


# =============================================================================
# CURRENCY FORMATTING
# =============================================================================


def format_currency(
    amount: Decimal | float | int,
    include_symbol: bool = True,
    include_pence: bool = True,
) -> str:
    """
    Format a monetary amount in GBP.

    Args:
        amount: Amount in pounds (or pence if specified)
        include_symbol: Whether to include the £ symbol
        include_pence: Whether to show pence (.00)

    Returns:
        Formatted string like "£1,234.56" or "1,234"
    """
    if isinstance(amount, (int, float)):
        amount = Decimal(str(amount))

    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    if include_pence:
        formatted = f"{amount:,.2f}"
    else:
        formatted = f"{int(amount):,}"

    if include_symbol:
        return f"£{formatted}"
    return formatted


def pence_to_pounds(pence: int) -> Decimal:
    """Convert pence to pounds."""
    return Decimal(pence) / Decimal(100)


def pounds_to_pence(pounds: Decimal | float) -> int:
    """Convert pounds to pence."""
    if isinstance(pounds, float):
        pounds = Decimal(str(pounds))
    return int((pounds * Decimal(100)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


# =============================================================================
# DATE & TIME UTILITIES
# =============================================================================


def get_london_now() -> datetime:
    """Get current datetime in London timezone."""
    return datetime.now(LONDON_TZ)


def format_date_uk(dt: datetime, include_day: bool = True) -> str:
    """
    Format a date in UK style.

    Args:
        dt: datetime object
        include_day: Include day of week (e.g., "Monday")

    Returns:
        String like "Monday, 4th December 2024" or "4th December 2024"
    """
    day = dt.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

    if include_day:
        return dt.strftime(f"%A, {day}{suffix} %B %Y")
    return dt.strftime(f"{day}{suffix} %B %Y")


def format_time_uk(dt: datetime, include_seconds: bool = False) -> str:
    """Format time in UK 12-hour format."""
    if include_seconds:
        return dt.strftime("%I:%M:%S %p").lstrip("0")
    return dt.strftime("%I:%M %p").lstrip("0")


def get_next_working_day(from_date: Optional[datetime] = None) -> datetime:
    """Get the next working day (Mon-Fri) from a given date."""
    if from_date is None:
        from_date = get_london_now()

    next_day = from_date + timedelta(days=1)

    # Skip weekends
    while next_day.weekday() >= 5:  # Saturday = 5, Sunday = 6
        next_day += timedelta(days=1)

    return next_day


def get_working_days_ahead(days: int, from_date: Optional[datetime] = None) -> datetime:
    """Get a date that is N working days ahead."""
    if from_date is None:
        from_date = get_london_now()

    current = from_date
    working_days_counted = 0

    while working_days_counted < days:
        current += timedelta(days=1)
        if current.weekday() < 5:  # Monday to Friday
            working_days_counted += 1

    return current


def humanize_time_ago(dt: datetime) -> str:
    """
    Convert a datetime to a human-readable 'time ago' string.

    Examples: "just now", "5 minutes ago", "2 hours ago", "yesterday"
    """
    now = get_london_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=LONDON_TZ)

    diff = now - dt

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 172800:
        return "yesterday"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    else:
        return format_date_uk(dt, include_day=False)


# =============================================================================
# TEXT UTILITIES
# =============================================================================


def title_case_name(name: str) -> str:
    """
    Properly title case a person's name, handling edge cases.

    Handles: McDonald, O'Brien, van der Berg, etc.
    """
    if not name:
        return ""

    # Special prefixes that should be lowercase
    lowercase_prefixes = {"van", "de", "der", "von", "la", "le", "du"}

    # Special handling patterns
    name = name.strip()

    words = name.split()
    result = []

    for i, word in enumerate(words):
        lower_word = word.lower()

        # Handle prefixes (lowercase unless first word)
        if lower_word in lowercase_prefixes and i > 0:
            result.append(lower_word)
        # Handle Mc/Mac names
        elif lower_word.startswith("mc") and len(word) > 2:
            result.append("Mc" + word[2:].capitalize())
        elif lower_word.startswith("mac") and len(word) > 3:
            result.append("Mac" + word[3:].capitalize())
        # Handle O' names
        elif lower_word.startswith("o'") and len(word) > 2:
            result.append("O'" + word[2:].capitalize())
        # Handle hyphenated names
        elif "-" in word:
            result.append("-".join(part.capitalize() for part in word.split("-")))
        else:
            result.append(word.capitalize())

    return " ".join(result)


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length, adding suffix if truncated."""
    if not text or len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)].rstrip() + suffix


def sanitize_for_filename(text: str) -> str:
    """
    Sanitize a string for use as a filename.

    Removes or replaces characters not safe for filesystems.
    """
    # Replace spaces with underscores
    text = text.replace(" ", "_")

    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        text = text.replace(char, "")

    # Remove any non-ASCII characters
    text = text.encode("ascii", "ignore").decode()

    # Limit length
    return text[:100]


def extract_budget_from_text(text: str) -> Optional[str]:
    """
    Extract a budget amount or range from free text.

    Returns budget band category or None.
    """
    if not text:
        return None

    text_lower = text.lower()

    # Look for explicit amounts
    amount_pattern = re.compile(r"£?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:k|thousand|K)?")
    matches = amount_pattern.findall(text_lower.replace(",", ""))

    amounts = []
    for match in matches:
        try:
            amount = float(match.replace(",", ""))
            # Check if 'k' or 'thousand' follows
            if "k" in text_lower or "thousand" in text_lower:
                if amount < 1000:
                    amount *= 1000
            amounts.append(amount)
        except ValueError:
            continue

    if not amounts:
        return None

    # Use the maximum amount mentioned (usually the budget)
    max_amount = max(amounts)

    # Map to budget bands
    if max_amount < 15000:
        return "under-15k"
    elif max_amount < 40000:
        return "15k-40k"
    elif max_amount < 100000:
        return "40k-100k"
    elif max_amount < 250000:
        return "100k-250k"
    else:
        return "over-250k"


# =============================================================================
# LEAD SCORING UTILITIES
# =============================================================================


def calculate_lead_score(
    service_type: str,
    budget_band: str,
    timeline: str,
    postcode: str,
    conservation_area: str = "unknown",
    source: str = "website",
) -> dict[str, Any]:
    """
    Calculate a lead score based on various factors.

    Returns a dict with score, priority, and reasoning.
    """
    score = 50  # Base score
    reasons = []

    # Service type scoring
    service_scores = {
        "basement": 25,
        "full-renovation": 20,
        "kitchen-extension": 15,
        "loft-conversion": 15,
        "bathroom": 5,
        "maintenance": -10,
        "other": 0,
    }
    service_bonus = service_scores.get(service_type, 0)
    score += service_bonus
    if service_bonus > 0:
        reasons.append(f"{service_type.replace('-', ' ').title()} project (+{service_bonus})")

    # Budget scoring
    budget_scores = {
        "over-250k": 30,
        "100k-250k": 25,
        "40k-100k": 15,
        "15k-40k": 0,
        "under-15k": -10,
        "unknown": 0,
    }
    budget_bonus = budget_scores.get(budget_band, 0)
    score += budget_bonus
    if budget_bonus != 0:
        reasons.append(f"Budget: {budget_band} ({'+' if budget_bonus > 0 else ''}{budget_bonus})")

    # Timeline scoring
    timeline_scores = {
        "asap": 20,
        "1-3-months": 15,
        "3-6-months": 5,
        "6-12-months": -5,
        "just-exploring": -15,
        "unknown": 0,
    }
    timeline_bonus = timeline_scores.get(timeline, 0)
    score += timeline_bonus
    if timeline_bonus != 0:
        reasons.append(f"Timeline: {timeline} ({'+' if timeline_bonus > 0 else ''}{timeline_bonus})")

    # Location scoring
    postcode_info = parse_postcode(postcode)
    if postcode_info:
        if postcode_info["is_premium_area"]:
            score += 10
            reasons.append(f"Premium area: {postcode_info['area_name']} (+10)")
        elif postcode_info["in_service_area"]:
            tier = get_service_area_tier(postcode)
            if tier == "primary":
                score += 5
                reasons.append("Primary service area (+5)")
        else:
            score -= 30
            reasons.append("Outside service area (-30)")
    else:
        score -= 10
        reasons.append("Invalid postcode (-10)")

    # Conservation area bonus (we specialize)
    if conservation_area == "yes":
        score += 10
        reasons.append("Conservation area expertise (+10)")

    # Source scoring
    source_scores = {
        "referral": 15,
        "houzz": 10,
        "website": 5,
        "google-ads": 0,
        "whatsapp": 5,
        "phone": 10,
    }
    source_bonus = source_scores.get(source, 0)
    score += source_bonus
    if source_bonus > 0:
        reasons.append(f"Lead source: {source} (+{source_bonus})")

    # Cap score between 0 and 100
    score = max(0, min(100, score))

    # Determine priority
    if score >= 80:
        priority = "hot"
    elif score >= 60:
        priority = "warm"
    elif score >= 40:
        priority = "cool"
    else:
        priority = "cold"

    return {
        "score": score,
        "priority": priority,
        "reasons": reasons,
        "summary": "; ".join(reasons),
    }


# =============================================================================
# EXPORT
# =============================================================================

__all__ = [
    # Types
    "ValidationResult",
    "PostcodeInfo",
    # Postcode
    "validate_uk_postcode",
    "parse_postcode",
    "get_service_area_tier",
    "get_location_multiplier",
    # Phone
    "validate_uk_phone",
    "format_phone_display",
    # Email
    "validate_email",
    # Currency
    "format_currency",
    "pence_to_pounds",
    "pounds_to_pence",
    # Date/Time
    "get_london_now",
    "format_date_uk",
    "format_time_uk",
    "get_next_working_day",
    "get_working_days_ahead",
    "humanize_time_ago",
    # Text
    "title_case_name",
    "truncate_text",
    "sanitize_for_filename",
    "extract_budget_from_text",
    # Lead Scoring
    "calculate_lead_score",
]
