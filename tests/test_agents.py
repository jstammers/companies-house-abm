"""Tests for agent classes in the ABM."""

from companies_house_abm.agents import Firm, Household


class TestFirm:
    """Tests for Firm agent class."""

    def test_firm_initialization(self) -> None:
        """Test that a Firm can be initialized with basic parameters."""
        firm = Firm(
            agent_id=1,
            company_number="12345678",
            sector="62.01",
            region="UKI3",
            age_months=60,
            capital=100000,
            debt=70000,
            equity=30000,
        )

        assert firm.id == 1
        assert firm.company_number == "12345678"
        assert firm.sector == "62.01"
        assert firm.region == "UKI3"
        assert firm.age_months == 60
        assert firm.capital == 100000
        assert firm.debt == 70000
        assert firm.equity == 30000
        assert firm.alive is True

    def test_firm_default_values(self) -> None:
        """Test that Firm has reasonable default values."""
        firm = Firm(
            agent_id=2,
            company_number="87654321",
            sector="25.61",
            region="UKG3",
        )

        assert firm.age_months == 0
        assert firm.capital == 0.0
        assert firm.debt == 0.0
        assert firm.equity == 0.0
        assert firm.inventory == 0.0
        assert firm.price > 0  # Should have a default price
        assert firm.wage > 0  # Should have a default wage
        assert firm.markup == 0.2  # Default markup

    def test_firm_get_state(self) -> None:
        """Test that Firm.get_state() returns expected fields."""
        firm = Firm(
            agent_id=3,
            company_number="11111111",
            sector="01.11",
            region="UKD1",
            capital=50000,
            equity=15000,
        )

        state = firm.get_state()

        assert "id" in state
        assert "company_number" in state
        assert "sector" in state
        assert "region" in state
        assert "capital" in state
        assert "equity" in state
        assert "alive" in state
        assert state["id"] == 3
        assert state["company_number"] == "11111111"
        assert state["alive"] is True


class TestHousehold:
    """Tests for Household agent class."""

    def test_household_initialization(self) -> None:
        """Test that a Household can be initialized with basic parameters."""
        household = Household(
            agent_id=1001,
            region="UKI3",
            income_decile=5,
            wealth=25000,
            propensity_to_consume=0.85,
        )

        assert household.id == 1001
        assert household.region == "UKI3"
        assert household.income_decile == 5
        assert household.wealth == 25000
        assert household.propensity_to_consume == 0.85
        assert household.alive is True
        assert household.employed_by is None  # Initially unemployed

    def test_household_default_values(self) -> None:
        """Test that Household has reasonable default values."""
        household = Household(
            agent_id=1002,
            region="UKG3",
            income_decile=7,
        )

        assert household.wealth == 0.0
        assert household.propensity_to_consume == 0.8  # Default
        assert household.reservation_wage > 0  # Should have a default
        assert household.monthly_income == 0.0
        assert household.monthly_consumption == 0.0

    def test_household_get_state(self) -> None:
        """Test that Household.get_state() returns expected fields."""
        household = Household(
            agent_id=1003,
            region="UKD1",
            income_decile=3,
            wealth=5000,
        )

        state = household.get_state()

        assert "id" in state
        assert "region" in state
        assert "income_decile" in state
        assert "wealth" in state
        assert "employed_by" in state
        assert "reservation_wage" in state
        assert "alive" in state
        assert state["id"] == 1003
        assert state["region"] == "UKD1"
        assert state["income_decile"] == 3
        assert state["wealth"] == 5000
        assert state["alive"] is True


class TestAgentInteractions:
    """Tests for agent interactions (placeholder for future)."""

    def test_multiple_agents_can_coexist(self) -> None:
        """Test that multiple agents can be created without conflicts."""
        firms = [
            Firm(
                agent_id=i,
                company_number=f"1234567{i}",
                sector="62.01",
                region="UKI3",
            )
            for i in range(10)
        ]

        households = [
            Household(
                agent_id=1000 + i,
                region="UKI3",
                income_decile=(i % 10) + 1,
            )
            for i in range(20)
        ]

        assert len(firms) == 10
        assert len(households) == 20

        # Check unique IDs
        firm_ids = {f.id for f in firms}
        household_ids = {h.id for h in households}

        assert len(firm_ids) == 10
        assert len(household_ids) == 20
        assert len(firm_ids.intersection(household_ids)) == 0  # No ID conflicts
