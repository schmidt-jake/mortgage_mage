import logging
from abc import ABC, abstractmethod, abstractproperty
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import requests
import structlog
import tenacity
import xarray as xr

logger = structlog.get_logger()


class RateScraper(ABC):
    def __init__(self, price: float, loan_to_value: float, fico_score: int):
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
    def extract_rates(self, response) -> pd.Series:
        pass

    @tenacity.retry(
        retry=tenacity.retry_if_exception_type((requests.ReadTimeout, requests.HTTPError)),
        wait=tenacity.wait_fixed(2),
        after=tenacity.after_log(logger, logging.WARN),
        stop=tenacity.stop_after_attempt(3),
    )
    def _get(self, params) -> requests.Response:
        response = requests.get(
            url=self.url,
            params=params,  # type: ignore
            timeout=10,
        )
        response.raise_for_status()
        return response

    def __call__(self):
        params = self.query_params()
        logger.info("GETting rates...", **params)
        response = self._get(params)
        response = response.json()
        rates = self.extract_rates(response)
        rates.name = "num_lenders"
        rates.index = rates.index.astype(float) / 100
        rates.index.name = "interest_rate"
        return rates


class CFPBScraper(RateScraper):
    @property
    def url(self):
        return "https://www.consumerfinance.gov/oah-api/rates/rate-checker"

    def query_params(self):
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

    def extract_rates(self, response):
        return pd.Series(response["data"])


class BankrateScraper(RateScraper):
    @property
    def url(self):
        return "https://www.myfinance.com/api/mortgages/purchase/30yr_fixed"

    def query_params(self):
        return {
            "zipcode": 77008,
            "loan_amount": int(self.price * self.loan_to_value),
            "fico_score": self.fice_score,
            "loan_to_value": self.loan_to_value,
            "product_family": "conventional",
            "property_type": "SingleFamily",
            "property_use": "PrimaryResidence",
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

    def extract_rates(self, response) -> pd.Series:
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
        for fico_score in range(650, 800, 10)
        for price in range(370_000, 400_000, 10_000)
        for scraper in [BankrateScraper, CFPBScraper]
    ]
    with ThreadPoolExecutor() as executor:
        results = executor.map(query, scrapers)
    x = pd.concat(
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
    x = xr.Dataset.from_dataframe(x.unstack("source"))
    return x
