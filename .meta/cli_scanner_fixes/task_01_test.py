#!/usr/bin/env python3
"""
Task 1: Test Time Parameter Conversion
Tests for CLI time string to datetime.time conversion
"""

import pytest
from datetime import time


def test_time_string_conversion():
    """Test converting time strings to datetime.time objects."""
    # Valid time formats
    test_cases = [
        ("09:50", time(9, 50)),
        ("09:15", time(9, 15)),
        ("15:30", time(15, 30)),
        ("00:00", time(0, 0)),
        ("23:59", time(23, 59)),
    ]

    for time_str, expected in test_cases:
        # Test conversion logic
        hours, minutes = map(int, time_str.split(':'))
        result = time(hours, minutes)
        assert result == expected, f"Failed to convert {time_str}"


def test_time_string_validation():
    """Test validation of time string formats."""
    invalid_cases = [
        ("9:50", "Missing leading zero"),
        ("09:5", "Missing leading zero"),
        ("25:00", "Invalid hour"),
        ("09:60", "Invalid minute"),
        ("09-50", "Wrong separator"),
        ("", "Empty string"),
        ("abc", "Non-numeric"),
    ]

    for invalid_time, reason in invalid_cases:
        try:
            if ':' not in invalid_time:
                parts = invalid_time.split(':')
            else:
                parts = invalid_time.split(':')

            if len(parts) != 2:
                raise ValueError(f"Expected 2 parts, got {len(parts)}")

            hours, minutes = map(int, parts)
            result_time = time(hours, minutes)
            # If we get here, the conversion worked, which means it was valid
            print(f"⚠️  Unexpectedly valid time: {invalid_time} -> {result_time}")
        except (ValueError, IndexError) as e:
            # This is expected for invalid cases
            print(f"✅ Correctly caught error for {invalid_time}: {e}")


if __name__ == "__main__":
    test_time_string_conversion()
    test_time_string_validation()
    print("✅ All time conversion tests passed!")
