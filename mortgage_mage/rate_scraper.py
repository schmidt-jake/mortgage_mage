import numpy as np
import pandas as pd
import requests
import structlog

logger = structlog.get_logger()


def get_rate_distribution(
    price: int,
    loan_amount: int,
    minfico: int,
    maxfico: int,
    state: str,
    rate_structure: str,
    loan_term: int,
    loan_type: str,
) -> pd.Series:
    params = {
        "price": price,
        "loan_amount": loan_amount,
        "minfico": minfico,
        "maxfico": maxfico,
        "state": state,
        "rate_structure": rate_structure,
        "loan_term": loan_term,
        "loan_type": loan_type,
    }
    logger.info("GETting rates...", **params)
    response = requests.get(
        url="https://www.consumerfinance.gov/oah-api/rates/rate-checker",
        params=params,  # type: ignore
        timeout=2,
    )
    response.raise_for_status()
    data = pd.Series(response.json()["data"], name="num_lenders")
    data.index = data.index.astype(float) / 100
    data.index.name = "interest_rate"
    return data


def sweep(
    price: int,
    fico: int,
    min_loan_to_value: float = 0.8,
    loan_to_value_interval: float = 0.01,
) -> pd.DataFrame:
    data = pd.DataFrame(
        {
            loan_to_value: get_rate_distribution(
                price=price,
                loan_amount=int(loan_to_value * price),
                minfico=fico,
                maxfico=fico,
                state="TX",
                rate_structure="fixed",
                loan_term=30,
                loan_type="conf",
            )
            for loan_to_value in np.arange(
                start=min_loan_to_value,
                stop=1.0,
                step=loan_to_value_interval,
            ).round(2)
        }
    )
    data.columns.name = "loan_to_value"
    return data
