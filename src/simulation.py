from abc import ABC, abstractmethod
from typing import Generator, Optional, Tuple

import numpy_financial as npf
import pandas as pd

# import pymc3 as pm
# from pydantic import BaseModel, Field


# class Normal(BaseModel):
#     mean: float
#     std: float

#     def distribution(self, **kwargs) -> pm.Normal:
#         return pm.Normal(mu=self.mean, sigma=self.std, **kwargs)


# class PositiveTruncatedNormal(Normal):
#     upper: Optional[float] = Field(default=None, gt=0)

#     def distribution(self, **kwargs) -> pm.TruncatedNormal:
#         return pm.TruncatedNormal(
#             mu=self.mean, sigma=self.std, lower=0, upper=self.upper, **kwargs
#         )


# class Poisson(BaseModel):
#     rate: float = Field(gt=0)

#     def distribution(self, **kwargs) -> pm.Poisson:
#         return pm.Poisson(mu=self.rate, **kwargs)


# class Config(BaseModel):
#     monthly_rent_revenue: PositiveTruncatedNormal
#     annual_property_tax_rate: PositiveTruncatedNormal
#     annual_property_appreciation_rate: Normal
#     risk_free_rate: float = Field(gt=0)
#     holding_period_months: int = Field(gt=0)
#     annual_fixed_costs: float = Field(gt=0)
#     monthly_variable_costs: Poisson
#     startup_costs: float = Field(gt=0)
#     num_simulations: int = Field(gt=0)
#     purchase_price: float = Field(gt=0)


class Simulator(ABC):
    def __init__(
        self,
        num_months: int,
        loan_amount: float,
        purchase_price: float,
        appreciation_rate: float,
    ):
        self.num_months = num_months
        self.loan_amount = loan_amount
        self.purchase_price = purchase_price
        self.appreciation_rate = appreciation_rate
        self.reset()

    def reset(self) -> None:
        self.principal_payments = 0.0

    def loan_to_value(self, i: int) -> float:
        appreciation_factor = (1 + self.appreciation_rate) ** (i / 12)
        return (self.loan_amount - self.principal_payments) / (
            self.purchase_price * appreciation_factor
        )

    def pay_principal(self, payment: float) -> None:
        self.principal_payments += payment

    def cash_flows(self) -> Generator[Tuple[int, float], None, None]:
        yield 0, self.on_purchase()
        for i in range(self.num_months):
            cash_flow = 0.0
            cash_flow += self.on_month_begin(i)
            cash_flow += self.on_month_end(i)
            if i > 1 and i % 12 == 0:
                cash_flow += self.on_year_end(i)
                cash_flow += self.on_year_begin(i)
            yield i, cash_flow
        yield self.num_months, self.on_sale()

    def run(self, discount_rate: float) -> float:
        self.reset()
        monthly_rate = (1 + discount_rate) ** (1 / 12) - 1
        cash_flows = pd.DataFrame(self.cash_flows(), columns=["month", "cash_flow"])
        cash_flows = cash_flows.groupby("month")["cash_flow"].sum()
        cash_flows = cash_flows.reindex(
            pd.RangeIndex(start=0, stop=self.num_months + 1)
        ).fillna(0.0)
        monthly_irr = npf.irr(cash_flows.values)
        return (1 + monthly_irr) ** (self.num_months / 12) - 1
        # npv = npf.npv(monthly_rate, cash_flows.values)
        # return (npv / -self.on_purchase()) ** (12 / self.num_months) - 1

    @abstractmethod
    def on_purchase(self) -> float:
        pass

    @abstractmethod
    def on_month_begin(self, i: int) -> float:
        pass

    @abstractmethod
    def on_month_end(self, i: int) -> float:
        pass

    @abstractmethod
    def on_year_begin(self, i: int) -> float:
        pass

    @abstractmethod
    def on_year_end(self, i: int) -> float:
        pass

    @abstractmethod
    def on_sale(self) -> float:
        pass


class MySimulator(Simulator):
    def on_purchase(self) -> float:
        return -20_000

    def on_month_begin(self, i: int) -> float:
        rent = 3_000
        interest_payment = 850
        principal_payment = 680
        escrow_payment = 763
        mortgage_payment = interest_payment + principal_payment + escrow_payment
        if self.loan_to_value(i) > 0.80:
            pmi_payment = 116
            mortgage_payment += pmi_payment
        self.pay_principal(principal_payment)
        return -mortgage_payment + rent

    def on_month_end(self, i: int) -> float:
        utility_expense = 300
        return -utility_expense

    def on_year_begin(self, i: int) -> float:
        return 0

    def on_year_end(self, i: int) -> float:
        return 0

    def on_sale(self) -> float:
        loan_balance = self.loan_amount - self.principal_payments
        sales_price = self.purchase_price * (1 + self.appreciation_rate) ** (
            self.num_months / 12
        )
        closing_costs = 0.06 * sales_price
        return sales_price - loan_balance - closing_costs


# def build_model(config: Config):
#     monthly_rent_revenue = config.monthly_rent_revenue.distribution(
#         shape=config.num_simulations
#     )
#     annual_property_tax_rate = config.annual_property_tax_rate.distribution(
#         shape=config.num_simulations
#     )
#     annual_property_appreciation_rate = (
#         config.annual_property_appreciation_rate.distribution(
#             shape=config.num_simulations
#         )
#     )
#     rents = monthly_rent_revenue.random(size=config.holding_period_months)
#     tax_rates = annual_property_tax_rate.random(size=config.holding_period_months // 12)
#     appr = annual_property_appreciation_rate.random(
#         size=config.holding_period_months // 12
#     )
