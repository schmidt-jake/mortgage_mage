import logging

from mortgage_mage.simulation import Mortgage, Property, Simulator

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    property = Property(
        purchase_price=394_900, tax_rate=0.019, annual_insurance_cost=3_000, taxable_value=394_900, market_value=394_900
    )
    mortgage = Mortgage(term_months=360, amount=property.purchase_price * 0.95, interest_rate=0.0275)
    simulator = Simulator(property=property, mortgage=mortgage, holding_period_months=60)
    print(simulator.irr)
    print(simulator.cash_on_cash_return)
