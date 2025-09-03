#!/usr/bin/env python3
"""
Test cases for Higher Tenure (HYT) exemption logic in board_filter.py

This script tests two scenarios:
1. Member who should be INELIGIBLE due to HYT (outside exemption period)
2. Member who should be ELIGIBLE (within exemption period)

Exception HYT Period: December 8, 2023 to September 30, 2026
"""

import sys
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from board_filter import board_filter
from constants import EXCEPTION_HYT_START_DATE, EXCEPTION_HYT_END_DATE, MAIN_HIGHER_TENURE, EXCEPTION_HIGHER_TENURE


def print_test_info():
    """Print information about the HYT exemption period and limits"""
    print("=" * 80)
    print("HYT EXEMPTION TEST CASES")
    print("=" * 80)
    print(
        f"Exception HYT Period: {EXCEPTION_HYT_START_DATE.strftime('%d %B %Y')} to {EXCEPTION_HYT_END_DATE.strftime('%d %B %Y')}")
    print()
    print("HYT Limits by Grade:")
    print("Grade | Main HYT | Exception HYT | Difference")
    print("-" * 45)
    for grade in ['SRA', 'SSG', 'TSG', 'MSG', 'SMS']:
        main = MAIN_HIGHER_TENURE.get(grade, 'N/A')
        exception = EXCEPTION_HIGHER_TENURE.get(grade, 'N/A')
        diff = exception - main if isinstance(main, int) and isinstance(exception, int) else 'N/A'
        print(f"{grade:5} | {main:8} | {exception:13} | +{diff} years")
    print("=" * 80)
    print()


def create_test_member(name, grade, year, tafmsd_date, dor_date, description):
    """Create a test member with the given parameters"""
    return {
        'name': name,
        'grade': grade,
        'year': year,
        'date_of_rank': dor_date.strftime('%d-%b-%Y'),
        'uif_code': None,
        'uif_disposition_date': None,
        'tafmsd': tafmsd_date.strftime('%d-%b-%Y'),
        're_status': None,
        'pafsc': '3S0X1',  # Valid AFSC with skill level 3
        'two_afsc': None,
        'three_afsc': None,
        'four_afsc': None,
        'description': description,
        'expected_hyt_date': tafmsd_date + relativedelta(years=MAIN_HIGHER_TENURE.get(grade)),
        'exception_hyt_date': tafmsd_date + relativedelta(years=EXCEPTION_HIGHER_TENURE.get(grade))
    }


def test_hyt_exemption():
    """Test HYT exemption logic with two test cases"""

    print_test_info()

    # Test Case 1: Member who should be INELIGIBLE due to HYT (outside exemption period)
    # HYT date falls BEFORE the exemption period starts
    test_member_1 = create_test_member(
        name="SSgt Smith (Should FAIL HYT)",
        grade='SSG',
        year=2024,
        tafmsd_date=datetime(2003, 1, 15),  # 21 years ago - exceeds main HYT of 20 years
        dor_date=datetime(2018, 6, 1),  # Adequate TIG
        description="HYT date falls BEFORE exemption period - should be INELIGIBLE"
    )

    # Test Case 2: Member who should be ELIGIBLE (within exemption period)
    # HYT date falls WITHIN the exemption period
    test_member_2 = create_test_member(
        name="SSgt Johnson (Should PASS with exemption)",
        grade='SSG',
        year=2024,
        tafmsd_date=datetime(2004, 6, 15),  # ~20 years ago - right at HYT limit
        dor_date=datetime(2019, 3, 1),  # Adequate TIG
        description="HYT date falls WITHIN exemption period - should be ELIGIBLE"
    )

    test_cases = [test_member_1, test_member_2]

    for i, member in enumerate(test_cases, 1):
        print(f"TEST CASE {i}: {member['name']}")
        print("-" * 60)
        print(f"Description: {member['description']}")
        print(f"Grade: {member['grade']}")
        print(f"TAFMSD: {member['tafmsd']}")
        print(f"DOR: {member['date_of_rank']}")
        print(f"Main HYT Limit: {MAIN_HIGHER_TENURE.get(member['grade'])} years")
        print(f"Exception HYT Limit: {EXCEPTION_HIGHER_TENURE.get(member['grade'])} years")
        print(f"Calculated Main HYT Date: {member['expected_hyt_date'].strftime('%d %B %Y')}")
        print(f"Calculated Exception HYT Date: {member['exception_hyt_date'].strftime('%d %B %Y')}")

        # Check if HYT date falls within exemption period
        main_hyt_in_exemption = EXCEPTION_HYT_START_DATE < member['expected_hyt_date'] < EXCEPTION_HYT_END_DATE
        print(f"Main HYT date within exemption period: {main_hyt_in_exemption}")

        # Run the board filter test
        result = board_filter(
            grade=member['grade'],
            year=member['year'],
            date_of_rank=member['date_of_rank'],
            uif_code=member['uif_code'],
            uif_disposition_date=member['uif_disposition_date'],
            tafmsd=member['tafmsd'],
            re_status=member['re_status'],
            pafsc=member['pafsc'],
            two_afsc=member['two_afsc'],
            three_afsc=member['three_afsc'],
            four_afsc=member['four_afsc']
        )

        print(f"\nRESULT: {result}")

        # Analyze the result
        if result is True:
            print("✅ ELIGIBLE for promotion board")
        elif result is False:
            print("❌ INELIGIBLE - No specific reason provided")
        elif isinstance(result, tuple) and len(result) == 2:
            eligible, reason = result
            if eligible:
                print(f"✅ ELIGIBLE - {reason}")
            else:
                print(f"❌ INELIGIBLE - {reason}")
        else:
            print(f"⚠️  Unexpected result format: {result}")

        # Expected vs Actual
        if i == 1:
            # Test Case 1 should be ineligible due to HYT
            if isinstance(result, tuple) and not result[0] and 'tenure' in result[1].lower():
                print("✅ EXPECTED RESULT: Correctly identified as ineligible due to HYT")
            else:
                print("❌ UNEXPECTED RESULT: Should have been ineligible due to HYT")
        elif i == 2:
            # Test Case 2 should be eligible (exemption should apply)
            if result is True or (isinstance(result, tuple) and result[0]):
                print("✅ EXPECTED RESULT: Correctly identified as eligible (exemption applied)")
            else:
                print("❌ UNEXPECTED RESULT: Should have been eligible due to HYT exemption")

        print("=" * 80)
        print()


if __name__ == "__main__":
    test_hyt_exemption()