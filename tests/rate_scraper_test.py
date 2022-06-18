from mortgage_mage.rate_scraper import BankrateScraper
from mortgage_mage.simulation import Property


def test_bankrate_scraper() -> None:
    _property = Property(
        purchase_price=394_900.0,
        tax_rate=0.019,
        annual_insurance_cost=1_800.0,
        taxable_value=420_000.0,
        market_value=450_000.0,
    )
    scraper = BankrateScraper(
        price=_property.purchase_price,
        loan_to_value=0.9,
        fico_score=750,
    )
    print(scraper())
