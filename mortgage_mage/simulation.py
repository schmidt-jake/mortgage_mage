from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Final, Generator, NamedTuple, Tuple

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


class Property(object):
    def __init__(self, purchase_price: float, tax_rate: float, annual_insurance_cost: float):
        self.purchase_price: Final = purchase_price
        self.value = purchase_price
        self.tax_rate = tax_rate
        self.annual_insurance_cost = annual_insurance_cost

    @property
    def tax_liability(self) -> float:
        taxable_value = self.value
        return taxable_value * self.tax_rate

    @property
    def escrow_payment(self) -> float:
        return (self.tax_liability + self.annual_insurance_cost) / 12


class Mortgage(object):
    class Payment(NamedTuple):
        principal: float
        interest: float

    def __init__(self, term_months: int, amount: int, interest_rate: float):
        self.term_months: Final = term_months
        self.amount: Final = amount
        self.interest_rate = interest_rate
        self.principal_paid = 0.0

    def payment(self, month: int) -> Mortgage.Payment:
        monthly_rate = (1 + self.interest_rate) ** (1 / 12) - 1
        interest = -npf.ipmt(
            rate=monthly_rate,
            per=month,
            nper=self.term_months,
            pv=self.amount,
        ).squeeze()
        principal = -npf.ppmt(
            rate=monthly_rate,
            per=month,
            nper=self.term_months,
            pv=self.amount,
        )
        return Mortgage.Payment(
            interest=interest,
            principal=principal,
        )

    @property
    def balance(self) -> float:
        return self.amount - self.principal_paid

    def pay_principal(self, amount: float) -> None:
        self.principal_paid += amount


class SimulatorInterface(ABC):
    def __init__(self, property: Property, mortgage: Mortgage, holding_period_months: int):
        self.property = property
        self.mortgage = mortgage
        self.holding_period_months = holding_period_months
        self.reset()

    @property
    def loan_to_value(self) -> float:
        return self.mortgage.balance / self.property.value

    @property
    def down_payment(self) -> float:
        return self.property.purchase_price - self.mortgage.amount

    def __iter__(self) -> Generator[Tuple[int, float], None, None]:
        for month in range(self.holding_period_months):
            cash_flow = 0.0
            if month == 0:
                cash_flow += self.on_purchase()
            cash_flow += self.on_month_begin(month=month)
            cash_flow += self.on_month_end(month=month)
            # if i > 1 and i % 12 == 0:
            #     cash_flow += self.on_year_end(i)
            #     cash_flow += self.on_year_begin(i)
            yield month, cash_flow
        yield month, self.on_sale()

    def reset(self) -> None:
        self.mortgage.principal_paid = 0.0
        self.property.value = self.property.purchase_price

    @property
    def cash_flows(self) -> pd.Series:
        self.reset()
        cash_flows = pd.DataFrame(iter(self), columns=["month", "cash_flow"])
        cash_flows = cash_flows.groupby("month")["cash_flow"].sum()
        cash_flows = cash_flows.reindex(pd.RangeIndex(start=0, stop=self.holding_period_months + 1)).fillna(0.0)
        return cash_flows

    @property
    def irr(self) -> float:
        monthly_irr: float = npf.irr(self.cash_flows.values)
        return (1.0 + monthly_irr) ** (self.holding_period_months / 12.0) - 1.0

    @abstractmethod
    def on_purchase(self) -> float:
        pass

    @abstractmethod
    def on_month_begin(self, month: int) -> float:
        pass

    @abstractmethod
    def on_month_end(self, month: int) -> float:
        pass

    # @abstractmethod
    # def on_year_begin(self, i: int) -> float:
    #     pass

    # @abstractmethod
    # def on_year_end(self, i: int) -> float:
    #     pass

    @abstractmethod
    def on_sale(self) -> float:
        pass


class Simulator(SimulatorInterface):
    def on_purchase(self) -> float:
        # TODO: add any closing costs the seller didn't credit
        return -self.down_payment

    @property
    def monthly_rent(self) -> float:
        return 3_000.0

    @property
    def monthly_expenses(self) -> float:
        return 300

    def on_month_begin(self, month: int) -> float:
        pmt = self.mortgage.payment(month=month)
        mortgage_payment = pmt.principal + pmt.interest + self.property.escrow_payment
        if self.loan_to_value > 0.8:
            # pmi_payment = 116
            pmi_payment = 0.003 * self.mortgage.amount / 12
            mortgage_payment += pmi_payment
        self.mortgage.pay_principal(pmt.principal)
        return -mortgage_payment + self.monthly_rent

    def on_month_end(self, month: int) -> float:
        return -self.monthly_expenses

    # def on_year_begin(self, i: int) -> float:
    #     return 0

    # def on_year_end(self, i: int) -> float:
    #     return 0

    def on_sale(self) -> float:
        sales_price = self.property.value
        closing_costs = 0.06 * sales_price
        return sales_price - self.mortgage.balance - closing_costs


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
