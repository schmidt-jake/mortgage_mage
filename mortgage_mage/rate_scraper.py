from abc import ABC
from abc import abstractmethod
from abc import abstractproperty
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
import logging
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import requests
import structlog
from tenacity import after_log
from tenacity import retry
from tenacity import retry_if_exception_type
from tenacity import stop_after_attempt
from tenacity import wait_fixed
import xarray as xr

logger = structlog.get_logger()
_retry = retry(
    retry=retry_if_exception_type((requests.ReadTimeout, requests.HTTPError)),
    wait=wait_fixed(2),
    after=after_log(logger, logging.WARN),
    stop=stop_after_attempt(3),
)


class RateScraper(ABC):
    def __init__(self, price: float, loan_to_value: float, fico_score: int):
        if loan_to_value >= 1.0:
            raise ValueError(f"LTV of {loan_to_value} exceeds 1.0")
        if fico_score <= 350 or fico_score >= 850:
            raise ValueError(f"Invalid FICO score of {fico_score}")
        self.price = price
        self.loan_to_value = loan_to_value
        self.fice_score = fico_score

    @abstractproperty
    def url(self) -> str:
        pass

    @abstractmethod
    def query_params(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def extract_rates(self, response: Dict[str, Any]) -> pd.Series:
        pass

    @_retry
    def _get(self, params: Dict[str, Any]) -> requests.Response:
        response = requests.get(
            url=self.url,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        return response

    def __call__(self) -> pd.Series:
        params = self.query_params()
        logger.info("GETting rates...", **params)
        response = self._get(params)
        rates = self.extract_rates(response.json())
        rates.name = "num_lenders"
        rates.index = rates.index.astype(float) / 100
        rates.index.name = "interest_rate"
        return rates


class CFPBScraper(RateScraper):
    @property
    def url(self) -> str:
        return "https://www.consumerfinance.gov/oah-api/rates/rate-checker"

    def query_params(self) -> Dict[str, Any]:
        return {
            "price": self.price,
            "loan_amount": self.price * self.loan_to_value,
            "minfico": self.fice_score,
            "maxfico": self.fice_score,
            "state": "TX",
            "rate_structure": "fixed",
            "loan_term": 30,
            "loan_type": "conf",
        }

    def extract_rates(self, response: Dict[str, Any]) -> pd.Series:
        return pd.Series(response["data"])


class BankrateScraper(RateScraper):
    class PropertyType(str, Enum):
        SingleFamily: str = "SingleFamily"
        Townhouse: str = "Townhouse"
        Condo4OrFewerStories: str = "Condo4OrFewerStories"
        Condo5OrMoreStories: str = "Condo5OrMoreStories"
        Coop: str = "Coop"
        MobileOrManufactured: str = "MobileOrManufactured"
        Modular: str = "Modular"
        Leasehold: str = "Leasehold"
        MultiFamily2Units: str = "MultiFamily2Units"
        MultiFamily3Units: str = "MultiFamily3Units"
        MultiFamily4Units: str = "MultiFamily4Units"
        Pud: str = "Pud"

    class PropertyUse(str, Enum):
        PrimaryResidence: str = "PrimaryResidence"
        SecondaryOrVacation: str = "SecondaryOrVacation"
        InvestmentOrRental: str = "InvestmentOrRental"

    @property
    def url(self) -> str:
        return "https://www.myfinance.com/api/mortgages/purchase/30yr_fixed"

    def query_params(self) -> Dict[str, Any]:
        return {
            "zipcode": 77008,
            "loan_amount": int(self.price * self.loan_to_value),
            "fico_score": self.fice_score,
            "loan_to_value": self.loan_to_value,
            "product_family": "conventional",
            "property_type": BankrateScraper.PropertyType.SingleFamily,
            "property_use": BankrateScraper.PropertyUse.PrimaryResidence,
            "api_class": "BankrateMortgageRTPApi",
            "veteran_status": "NoMilitaryService",
            "had_prior_va_loan": False,
            "has_va_disabilities": False,
            "include_high_fees": True,
            "points": 0,
            "cash_out_amount": 0,
            "first_time_home_buyer": False,
            "full_feed": True,
            "allow_multiple": True,
        }

    def extract_rates(self, response: Dict[str, Any]) -> pd.Series:
        df = pd.json_normalize(response["results"])
        rates = df["rate"].value_counts()
        return rates


def sweep() -> xr.Dataset:
    def query(scraper: RateScraper) -> Tuple[RateScraper, pd.Series]:
        rates = scraper()
        return scraper, rates

    scrapers = [
        scraper(price=price, loan_to_value=ltv, fico_score=fico_score)
        for ltv in np.arange(0.90, 0.97, 0.01).round(2)
        for fico_score in range(650, 850, 10)
        for price in range(370_000, 400_000, 10_000)
        for scraper in [BankrateScraper, CFPBScraper]
    ]
    with ThreadPoolExecutor() as executor:
        results = executor.map(query, scrapers)
    x_df = pd.concat(
        {
            (
                scraper.__class__.__name__,
                scraper.loan_to_value,
                scraper.fice_score,
                scraper.price,
            ): rates
            for scraper, rates in results
        },
        names=["source", "ltv", "fico_score", "price"],
    )
    x = xr.Dataset.from_dataframe(x_df.unstack("source"))
    return x
