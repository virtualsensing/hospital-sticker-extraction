"""Tests for field formatting and validation."""

import pytest
from extractor.fields import (
    format_dob,
    format_patient_name,
    format_doctor,
    format_ward,
    format_phone,
    combine_medical_aid,
    validate_record,
)


class TestFormatDOB:
    def test_dd_mm_yyyy(self):
        assert format_dob("20/02/1949") == "20 Feb 1949"

    def test_dd_mm_yy_old(self):
        assert format_dob("06/12/46") == "06 Dec 1946"

    def test_dd_mm_yy_young(self):
        assert format_dob("06/10/04") == "06 Oct 2004"

    def test_already_formatted(self):
        assert format_dob("20 Feb 1949") == "20 Feb 1949"

    def test_empty(self):
        assert format_dob("") == ""
        assert format_dob(None) == ""

    def test_dash_separator(self):
        assert format_dob("14-05-1977") == "14 May 1977"

    def test_single_digit_day(self):
        assert format_dob("1/03/54") == "01 Mar 1954"

    def test_boundary_year_29(self):
        assert format_dob("01/01/29") == "01 Jan 2029"

    def test_boundary_year_30(self):
        assert format_dob("01/01/30") == "01 Jan 1930"


class TestFormatPatientName:
    def test_surname_first_with_title_end(self):
        assert format_patient_name("Smith John Mr") == "John Smith"

    def test_title_start_uppercase(self):
        assert format_patient_name("MR JAMES K WILLIAMS") == "James K Williams"

    def test_ms_title(self):
        assert format_patient_name("Jones Sarah Ms") == "Sarah Jones"

    def test_master_title(self):
        assert format_patient_name("Brown Tyler Master") == "Tyler Brown"

    def test_mrs_title(self):
        assert format_patient_name("Davis Maria Mrs") == "Maria Davis"

    def test_no_title(self):
        assert format_patient_name("John Smith") == "John Smith"

    def test_empty(self):
        assert format_patient_name("") == ""
        assert format_patient_name(None) == ""


class TestFormatDoctor:
    def test_hibiscus_format(self):
        assert format_doctor("Jones (0551234) D, DR") == "Dr D Jones"

    def test_already_correct(self):
        assert format_doctor("Dr D Jones") == "Dr D Jones"

    def test_uppercase_dr(self):
        assert format_doctor("DR D JONES") == "Dr D Jones"

    def test_empty(self):
        assert format_doctor("") == ""
        assert format_doctor(None) == ""


class TestFormatWard:
    def test_surg_with_bed(self):
        assert format_ward("SURG B502-1") == "SURG"

    def test_med_with_room(self):
        assert format_ward("MED R15.B") == "MED"

    def test_day_none(self):
        assert format_ward("DAY None") == "DAY"

    def test_plain_surg(self):
        assert format_ward("SURG") == "SURG"

    def test_lowercase(self):
        assert format_ward("surg") == "SURG"

    def test_empty(self):
        assert format_ward("") == ""


class TestFormatPhone:
    def test_prefers_cell(self):
        assert format_phone("0821234567", "0311234567") == "0821234567"

    def test_fallback_to_tel(self):
        assert format_phone("", "0311234567") == "0311234567"

    def test_ignores_placeholder(self):
        assert format_phone("", "(W)") == ""

    def test_cell_with_placeholder_tel(self):
        assert format_phone("0821234567", "(W)") == "0821234567"

    def test_both_empty(self):
        assert format_phone("", "") == ""


class TestCombineMedicalAid:
    def test_discovery_coastal_saver(self):
        result = combine_medical_aid("DISCOVERY HEALTH MED", "COASTAL SAVER")
        assert result == "Discovery Coastal Saver"

    def test_gems_ruby(self):
        result = combine_medical_aid("GEMS NON DENTAL", "RUBY")
        assert result == "Gems Non Dental Ruby"

    def test_gems_tanzanite(self):
        result = combine_medical_aid("GEMS NON DENTAL", "TANZANITE ONE")
        assert result == "Gems Non Dental Tanzanite One"

    def test_polmed_same(self):
        result = combine_medical_aid("POLMED", "POLMED")
        assert result == "Polmed"

    def test_hibiscus_scheme_only(self):
        result = combine_medical_aid("", "", scheme_field="Momentum Associated")
        assert result == "Momentum Associated"

    def test_coid(self):
        result = combine_medical_aid("COID", "MASSMART")
        assert result == "COID Massmart"

    def test_coid_no_employer(self):
        result = combine_medical_aid("COID", "")
        assert result == "COID"

    def test_empty(self):
        assert combine_medical_aid("", "") == ""


class TestValidateRecord:
    def test_valid_record(self):
        record = {
            "hospital_name": "Shelly Beach Hospital",
            "patient_name": "John Smith",
            "patient_id": "7203185047081",
            "date_of_birth": "12 Jun 1985",
        }
        assert validate_record(record) == []

    def test_missing_name(self):
        record = {"hospital_name": "Test", "patient_id": "7203185047081"}
        warnings = validate_record(record)
        assert any("Missing patient name" in w for w in warnings)

    def test_invalid_id(self):
        record = {
            "hospital_name": "Test",
            "patient_name": "Test",
            "patient_id": "12345",
        }
        warnings = validate_record(record)
        assert any("not a valid 13-digit" in w for w in warnings)

    def test_bad_dob_format(self):
        record = {
            "hospital_name": "Test",
            "patient_name": "Test",
            "patient_id": "7203185047081",
            "date_of_birth": "12/06/1985",
        }
        warnings = validate_record(record)
        assert any("not in expected format" in w for w in warnings)
