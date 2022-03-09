from mortgage_mage.rate_scraper import BankrateScraper
from mortgage_mage.simulation import Property


def test_bankrate_scraper() -> None:
    _property = Property(purchase_price=394_900, tax_rate=0.019, annual_insurance_cost=1_800)
    scraper = BankrateScraper(price=_property.purchase_price, loan_to_value=0.9, fico_score=750)
    print(scraper())
