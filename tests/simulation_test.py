from numpy.testing import assert_allclose

from mortgage_mage import simulation


def test_mortgage() -> None:
    term_months = 360
    amount = 400000.0
    mortgage = simulation.Mortgage(
        term_months=term_months,
        amount=amount,
        interest_rate=0.0275,
    )
    for month in range(term_months):
        payment = mortgage.monthly_payment(month)
        mortgage.pay_principal(amount=payment.principal)
    assert_allclose(mortgage.balance, 0.0, atol=1e-9)  # type: ignore[no-untyped-call]


def test_simulator() -> None:
    property = simulation.Property(
        purchase_price=394_900.0,
        tax_rate=0.019,
        annual_insurance_cost=1_800.0,
        value=394_900.0,
    )
    mortgage = simulation.Mortgage(
        term_months=360,
        amount=property.purchase_price * 0.95,
        interest_rate=0.0275,
    )
    sim = simulation.Simulator(
        property=property,
        mortgage=mortgage,
        holding_period_months=60,
    )
    print(sim.cash_flows)
    print(sim.irr)
    print(sim.equity)
    assert sim.irr > 0.0
