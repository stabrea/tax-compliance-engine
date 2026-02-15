"""Tests for the TaxRateDatabase."""

import pytest

from tax_engine.rates import (
    ExemptionCategory,
    LocalRate,
    StateRate,
    TaxRateDatabase,
)


@pytest.fixture
def db() -> TaxRateDatabase:
    return TaxRateDatabase()


# ── Known state rates ────────────────────────────────────────────────


def test_texas_base_rate(db: TaxRateDatabase):
    assert db.get_base_rate("TX") == 0.0625


def test_california_base_rate(db: TaxRateDatabase):
    assert db.get_base_rate("CA") == 0.0725


def test_new_york_base_rate(db: TaxRateDatabase):
    assert db.get_base_rate("NY") == 0.04


def test_oregon_has_no_sales_tax(db: TaxRateDatabase):
    assert db.get_base_rate("OR") == 0.0


def test_delaware_has_no_sales_tax(db: TaxRateDatabase):
    assert db.get_base_rate("DE") == 0.0


def test_montana_has_no_sales_tax(db: TaxRateDatabase):
    assert db.get_base_rate("MT") == 0.0


def test_new_hampshire_has_no_sales_tax(db: TaxRateDatabase):
    assert db.get_base_rate("NH") == 0.0


def test_no_sales_tax_states_list(db: TaxRateDatabase):
    no_tax = db.no_sales_tax_states()
    for code in ["OR", "DE", "MT", "NH"]:
        assert code in no_tax
    # States with tax should NOT be in this list
    assert "TX" not in no_tax
    assert "CA" not in no_tax


def test_alaska_has_zero_base_but_local(db: TaxRateDatabase):
    state = db.get_state("AK")
    assert state is not None
    assert state.base_rate == 0.0
    assert state.has_local_taxes is True


def test_all_50_states_plus_dc_loaded(db: TaxRateDatabase):
    assert db.state_count == 51


def test_unknown_state_raises(db: TaxRateDatabase):
    with pytest.raises(ValueError, match="Unknown state code"):
        db.get_base_rate("ZZ")


def test_case_insensitive_lookup(db: TaxRateDatabase):
    assert db.get_base_rate("tx") == db.get_base_rate("TX")


# ── Exemption lookups ────────────────────────────────────────────────


def test_texas_exempts_grocery(db: TaxRateDatabase):
    assert db.is_exempt("TX", ExemptionCategory.GROCERY) is True


def test_texas_exempts_prescription_drug(db: TaxRateDatabase):
    assert db.is_exempt("TX", ExemptionCategory.PRESCRIPTION_DRUG) is True


def test_california_exempts_grocery(db: TaxRateDatabase):
    assert db.is_exempt("CA", ExemptionCategory.GROCERY) is True


def test_new_york_exempts_clothing(db: TaxRateDatabase):
    assert db.is_exempt("NY", ExemptionCategory.CLOTHING) is True


def test_mississippi_does_not_exempt_grocery(db: TaxRateDatabase):
    # MS taxes grocery at full rate
    assert db.is_exempt("MS", ExemptionCategory.GROCERY) is False


def test_states_exempting_grocery(db: TaxRateDatabase):
    grocery_exempt = db.states_exempting(ExemptionCategory.GROCERY)
    assert "TX" in grocery_exempt
    assert "CA" in grocery_exempt
    assert "NY" in grocery_exempt
    assert "MS" not in grocery_exempt


def test_states_exempting_clothing(db: TaxRateDatabase):
    clothing_exempt = db.states_exempting(ExemptionCategory.CLOTHING)
    assert "NY" in clothing_exempt
    assert "PA" in clothing_exempt
    assert "NJ" in clothing_exempt


# ── Local rate queries ───────────────────────────────────────────────


def test_get_local_rate_houston(db: TaxRateDatabase):
    local = db.get_local_rate("TX", "Houston")
    assert local is not None
    assert isinstance(local, LocalRate)
    assert local.rate == 0.02
    assert local.county == "Harris"


def test_get_combined_rate_houston(db: TaxRateDatabase):
    combined = db.get_combined_rate("TX", "Houston")
    # TX base 0.0625 + Houston local 0.02 = 0.0825
    assert combined == pytest.approx(0.0825, abs=0.001)


def test_get_local_rate_nonexistent_city(db: TaxRateDatabase):
    local = db.get_local_rate("TX", "Nonexistent City")
    assert local is None


def test_combined_rate_falls_back_to_avg_when_no_city(db: TaxRateDatabase):
    combined = db.get_combined_rate("TX")
    state = db.get_state("TX")
    assert combined == state.avg_combined_rate


def test_nyc_local_rate(db: TaxRateDatabase):
    local = db.get_local_rate("NY", "New York City")
    assert local is not None
    assert local.rate == 0.045


def test_highest_rate_states(db: TaxRateDatabase):
    top = db.highest_rate_states(5)
    assert len(top) == 5
    # Top states should have high avg combined rates
    assert all(s.avg_combined_rate > 0.08 for s in top)


def test_lowest_rate_states_excludes_zero(db: TaxRateDatabase):
    low = db.lowest_rate_states(5)
    assert len(low) == 5
    # Should not include no-tax states
    codes = [s.state_code for s in low]
    assert "OR" not in codes
    assert "DE" not in codes
    assert "MT" not in codes
    assert "NH" not in codes
