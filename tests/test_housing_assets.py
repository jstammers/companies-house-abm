"""Tests for housing asset dataclasses (Property and Mortgage)."""

from __future__ import annotations

from companies_house_abm.abm.assets.mortgage import Mortgage
from companies_house_abm.abm.assets.property import Property


class TestProperty:
    def test_default_property(self):
        p = Property()
        assert p.region == "south_east"
        assert p.property_type == "terraced"
        assert p.market_value == 285_000.0
        assert p.on_market is False
        assert p.owner_id is None

    def test_property_id_auto_generated(self):
        p1 = Property()
        p2 = Property()
        assert p1.property_id != p2.property_id

    def test_list_for_sale(self):
        p = Property(market_value=200_000.0)
        p.list_for_sale(initial_markup=0.05)
        assert p.on_market is True
        assert p.asking_price == 210_000.0
        assert p.months_listed == 0

    def test_reduce_price(self):
        p = Property(market_value=200_000.0)
        p.list_for_sale(initial_markup=0.05)
        assert p.asking_price == 210_000.0
        p.reduce_price(reduction_rate=0.10)
        assert p.asking_price == 189_000.0
        assert p.months_listed == 1

    def test_delist(self):
        p = Property()
        p.list_for_sale()
        p.delist()
        assert p.on_market is False
        assert p.asking_price == 0.0
        assert p.months_listed == 0

    def test_sell(self):
        p = Property(market_value=200_000.0, owner_id="seller_1")
        p.list_for_sale()
        p.sell(new_owner_id="buyer_1", sale_price=195_000.0, period=10)
        assert p.owner_id == "buyer_1"
        assert p.last_transaction_price == 195_000.0
        assert p.last_transaction_period == 10
        assert p.market_value == 195_000.0
        assert p.on_market is False

    def test_sell_clears_rental(self):
        p = Property(is_rented=True, tenant_id="tenant_1")
        p.sell(new_owner_id="buyer_1", sale_price=200_000.0, period=5)
        assert p.is_rented is False
        assert p.tenant_id is None

    def test_get_state(self):
        p = Property(region="london", property_type="flat")
        state = p.get_state()
        assert state["region"] == "london"
        assert state["property_type"] == "flat"
        assert "property_id" in state
        assert "market_value" in state


class TestMortgage:
    def test_default_mortgage(self):
        m = Mortgage()
        assert m.rate_type == "fixed"
        assert m.term_months == 300
        assert m.in_arrears is False

    def test_monthly_payment_calculated(self):
        m = Mortgage(principal=200_000.0, interest_rate=0.04, term_months=300)
        # Annuity payment for 200k at 4% over 25 years should be ~1,055
        assert 1050.0 < m.monthly_payment < 1060.0

    def test_monthly_payment_zero_rate(self):
        m = Mortgage(principal=120_000.0, interest_rate=0.0, term_months=300)
        assert m.monthly_payment == 400.0

    def test_current_ltv(self):
        m = Mortgage(outstanding=180_000.0)
        assert m.current_ltv(200_000.0) == 0.9

    def test_current_ltv_zero_value(self):
        m = Mortgage(outstanding=100_000.0)
        assert m.current_ltv(0.0) == float("inf")

    def test_amortize(self):
        m = Mortgage(
            principal=200_000.0,
            outstanding=200_000.0,
            interest_rate=0.04,
            term_months=300,
            remaining_months=300,
        )
        payment = m.amortize()
        assert payment == m.monthly_payment
        assert m.outstanding < 200_000.0
        assert m.remaining_months == 299

    def test_amortize_reduces_balance(self):
        m = Mortgage(
            principal=200_000.0,
            outstanding=200_000.0,
            interest_rate=0.04,
            term_months=300,
            remaining_months=300,
        )
        initial = m.outstanding
        m.amortize()
        # After one payment, outstanding should be less by principal portion
        monthly_rate = 0.04 / 12.0
        interest = initial * monthly_rate
        expected_outstanding = initial - (m.monthly_payment - interest)
        assert abs(m.outstanding - expected_outstanding) < 0.01

    def test_record_missed_payment(self):
        m = Mortgage()
        m.record_missed_payment()
        assert m.in_arrears is True
        assert m.arrears_months == 1
        m.record_missed_payment()
        assert m.arrears_months == 2

    def test_record_payment_resets_arrears(self):
        m = Mortgage()
        m.record_missed_payment()
        m.record_missed_payment()
        m.record_payment_made()
        assert m.in_arrears is False
        assert m.arrears_months == 0

    def test_get_state(self):
        m = Mortgage(borrower_id="hh_1", lender_id="bank_1")
        state = m.get_state()
        assert state["borrower_id"] == "hh_1"
        assert state["lender_id"] == "bank_1"
        assert "outstanding" in state
        assert "in_arrears" in state

    def test_mortgage_id_auto_generated(self):
        m1 = Mortgage()
        m2 = Mortgage()
        assert m1.mortgage_id != m2.mortgage_id
