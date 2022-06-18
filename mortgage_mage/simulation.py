from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import asdict
from dataclasses import dataclass
from typing import Final, Iterator, List

import numpy as np
import numpy_financial as npf
import pandas as pd


@dataclass
class Property(object):
    purchase_price: float
    tax_rate: float
    annual_insurance_cost: float
    taxable_value: float
    market_value: float

    @property
    def tax_liability(self) -> float:
        taxable_value = self.taxable_value
        # TODO: subtract tax deductions from taxable_value
        taxable_value -= 10_000.0
        return taxable_value * self.tax_rate

    @property
    def monthly_escrow_payment(self) -> float:
        return (self.tax_liability + self.annual_insurance_cost) / 12


class Mortgage(object):
    @dataclass
    class Payment(object):
        principal: float
        interest: float

    def __init__(self, term_months: int, amount: float, interest_rate: float):
        self.term_months: Final[int] = term_months
        self.amount: Final[float] = amount
        self.interest_rate: Final[float] = interest_rate
        self._principal_paid: float = 0.0

    def monthly_payment(self, month: int) -> Mortgage.Payment:
        monthly_rate = (1 + self.interest_rate) ** (1 / 12) - 1
        # monthly_rate = self.interest_rate / 12
        interest: np.float64 = -npf.ipmt(
            rate=monthly_rate,
            per=month + 1,
            nper=self.term_months,
            pv=self.amount,
            when="begin",
        )
        principal: np.float64 = -npf.ppmt(
            rate=monthly_rate,
            per=month + 1,
            nper=self.term_months,
            pv=self.amount,
            when="begin",
        )
        return Mortgage.Payment(
            interest=float(interest),
            principal=float(principal),
        )

    @property
    def balance(self) -> float:
        return self.amount - self._principal_paid

    def pay_principal(self, amount: float) -> None:
        self._principal_paid += amount


@dataclass
class CashFlow(object):
    cash_in: float = 0.0
    cash_out: float = 0.0

    @property
    def net(self) -> float:
        return self.cash_in - self.cash_out

    def __add__(self, other: CashFlow) -> CashFlow:
        return CashFlow(
            cash_in=self.cash_in + other.cash_in,
            cash_out=self.cash_out + other.cash_out,
        )


class SimulatorInterface(ABC):
    def __init__(self, property: Property, mortgage: Mortgage, holding_period_months: int):
        self.property = property
        self.mortgage = mortgage
        self.holding_period_months = holding_period_months
        self.down_payment = self.property.purchase_price - self.mortgage.amount
        self.reset()

    @property
    def loan_to_value(self) -> float:
        return self.mortgage.balance / self.property.taxable_value

    @property
    def equity(self) -> float:
        return self.property.taxable_value - self.mortgage.balance

    def __next__(self) -> CashFlow:
        if self.month == self.holding_period_months:
            raise StopIteration
        net_cash_flow = CashFlow()
        if self.month == 0:
            net_cash_flow += self.on_purchase()
        net_cash_flow += self.on_month_begin()
        net_cash_flow += self.on_month_end()
        if self.month % 12 == 0:
            net_cash_flow += self.on_year_end()
        if self.month == self.holding_period_months - 1:
            net_cash_flow += self.on_sale()
        self._cash_flows.append(net_cash_flow)
        self.month += 1
        return net_cash_flow

    def __iter__(self) -> Iterator[CashFlow]:
        self.reset()
        return self

    def reset(self) -> None:
        self.month = 0
        self.mortgage._principal_paid = 0.0
        self.property.taxable_value = self.property.purchase_price
        self._cash_flows: List[CashFlow] = []

    @property
    def cash_flows(self) -> pd.DataFrame:
        cash_flows = pd.DataFrame.from_records(
            [{"month": month, **asdict(cash_flow)} for month, cash_flow in enumerate(self)]
        )
        cash_flows["net"] = cash_flows["cash_in"] - cash_flows["cash_out"]
        return cash_flows

    @property
    def annual_cash_flows(self) -> pd.DataFrame:
        cash_flows = self.cash_flows
        annual_cash_flows = cash_flows.groupby(cash_flows.index // 12).sum()
        return annual_cash_flows

    @property
    def cash_on_cash_return(self) -> pd.Series:
        annual_cash_flows = self.annual_cash_flows
        cash_on_cash_return = annual_cash_flows["net"] / annual_cash_flows["cash_out"]
        cash_on_cash_return.name = "cash_on_cash_return"
        cash_on_cash_return.index.name = "year"
        return cash_on_cash_return

    @property
    def irr(self) -> float:
        annual_cash_flows = self.annual_cash_flows
        irr: float = npf.irr(annual_cash_flows["net"].values)
        return irr

    @abstractmethod
    def on_purchase(self) -> CashFlow:
        pass

    @abstractmethod
    def on_month_begin(self) -> CashFlow:
        pass

    @abstractmethod
    def on_month_end(self) -> CashFlow:
        pass

    def on_year_end(self) -> CashFlow:
        return CashFlow()

    @abstractmethod
    def on_sale(self) -> CashFlow:
        pass


# @dataclass
# class IncomeTax(object):
#     marginal_rate: float

#     def liability(self, net_income: float, ) -> float:
#         return taxable_income * self.marginal_rate


class Simulator(SimulatorInterface):
    _marginal_income_tax_rate: float = 0.32

    def on_purchase(self) -> CashFlow:
        # TODO: add any closing costs the seller didn't credit
        return CashFlow(cash_out=self.down_payment)

    @property
    def monthly_rent(self) -> float:
        return 3_600.0

    @property
    def monthly_expenses(self) -> float:
        return 0.0

    def on_month_begin(self) -> CashFlow:
        loan_payment = self.mortgage.monthly_payment(month=self.month)
        total_payment = loan_payment.principal + loan_payment.interest + self.property.monthly_escrow_payment
        if self.loan_to_value > 0.8:
            # pmi_payment = 116
            pmi_payment = 0.004 * self.mortgage.amount / 12
            total_payment += pmi_payment
        self.mortgage.pay_principal(loan_payment.principal)
        return CashFlow(cash_in=self.monthly_rent, cash_out=total_payment)

    def on_month_end(self) -> CashFlow:
        return CashFlow(cash_out=self.monthly_expenses)

    def on_year_end(self) -> CashFlow:
        # TODO: account for change in property's taxable value
        # self.property.taxable_value *= 0.98
        # self.property.market_value *= 0.98
        # TODO: pay income tax
        return CashFlow(cash_out=self.property.tax_liability)

    def on_sale(self) -> CashFlow:
        sales_price = self.property.market_value
        closing_costs = 0.06 * sales_price
        # TODO: is the right way to model the sale's cash flows?
        return CashFlow(
            cash_in=sales_price - self.mortgage.balance,
            cash_out=closing_costs,
        )


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
