"""
Phone Number Normalization Utilities

Ensures consistent phone number formatting across ingestion and analytics.
Normalizes to E.164 format with UAE country code (+971).
"""

import re
from typing import Optional


def normalize_phone(raw_phone: Optional[str]) -> Optional[str]:
    """
    Normalize phone number to E.164 format for UAE.
    
    Args:
        raw_phone: Raw phone number in any format
        
    Returns:
        Normalized phone in format: +971XXXXXXXXX or None if invalid
        
    Examples:
        '+971501234567' -> '+971501234567'
        '971501234567' -> '+971501234567'
        '0501234567' -> '+971501234567'
        '050 123 4567' -> '+971501234567'
        '050-123-4567' -> '+971501234567'
        '+97150 123 4567' -> '+971501234567'
    """
    if not raw_phone or not isinstance(raw_phone, str):
        return None
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', raw_phone)
    
    if not digits:
        return None
    
    # Handle different UAE formats
    if digits.startswith('971'):
        # Already has country code
        if len(digits) == 12:  # 971 + 9 digits
            return f'+{digits}'
    elif digits.startswith('0'):
        # Local UAE format (05X XXX XXXX)
        if len(digits) == 10:
            return f'+971{digits[1:]}'  # Remove leading 0
    elif len(digits) == 9:
        # Without leading 0 or country code
        return f'+971{digits}'
    
    # If none of the above, try to salvage
    if len(digits) >= 9:
        # Take last 9 digits
        return f'+971{digits[-9:]}'
    
    # Invalid phone number
    return None


def extract_digits_only(raw_phone: Optional[str]) -> Optional[str]:
    """
    Extract only digits from phone number.
    Useful for fuzzy matching when normalized formats don't match.
    
    Args:
        raw_phone: Raw phone number
        
    Returns:
        Digits only or None
    """
    if not raw_phone or not isinstance(raw_phone, str):
        return None
    
    digits = re.sub(r'\D', '', raw_phone)
    return digits if digits else None


def phones_match(phone1: Optional[str], phone2: Optional[str]) -> bool:
    """
    Check if two phone numbers match (accounting for formatting differences).
    
    Args:
        phone1: First phone number
        phone2: Second phone number
        
    Returns:
        True if phones match, False otherwise
    """
    norm1 = normalize_phone(phone1)
    norm2 = normalize_phone(phone2)
    
    if not norm1 or not norm2:
        return False
    
    return norm1 == norm2


# Example usage and tests
if __name__ == "__main__":
    test_cases = [
        ('+971501234567', '+971501234567'),
        ('971501234567', '+971501234567'),
        ('0501234567', '+971501234567'),
        ('050 123 4567', '+971501234567'),
        ('050-123-4567', '+971501234567'),
        ('+97150 123 4567', '+971501234567'),
        ('', None),
        (None, None),
        ('invalid', None),
    ]
    
    print("Testing phone normalization:\n")
    for raw, expected in test_cases:
        result = normalize_phone(raw)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{raw}' -> '{result}' (expected: '{expected}')")
    
    print("\n\nTesting phone matching:")
    test_matches = [
        ('+971501234567', '0501234567', True),
        ('971501234567', '050 123 4567', True),
        ('+971501234567', '+971509876543', False),
    ]
    
    for phone1, phone2, expected in test_matches:
        result = phones_match(phone1, phone2)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{phone1}' vs '{phone2}' -> {result} (expected: {expected})")
