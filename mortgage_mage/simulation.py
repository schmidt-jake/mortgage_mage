from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Final, Iterator, List

import numpy as np
import numpy_financial as npf
import pandas as pd


@dataclass
class Property(object):
    """
    A real estate asset.

    Parameters
    ----------
    purchase_price: float
    tax_rate: float
    annual_insurance_cost: float
    taxable_value: float
    market_value: float
    """

    purchase_price: float
    tax_rate: float
    annual_insurance_cost: float
    taxable_value: float
    market_value: float

    @property
    def tax_liability(self) -> float:
        """
        The taxable value of this asset.
        """
        taxable_value = self.taxable_value
        # TODO: subtract tax deductions from taxable_value
        taxable_value -= 10_000.0
        return taxable_value * self.tax_rate

    @property
    def monthly_escrow_payment(self) -> float:
        """
        The amount paid into an escrow account (usually held by the mortgage company)
        that is set aside for property tax and homeowner's insurance (which gets paid
        at the end of the year).
        """
        return (self.tax_liability + self.annual_insurance_cost) / 12


class Mortgage(object):
    @dataclass
    class Payment(object):
        principal: float
        interest: float

    def __init__(self, term_months: int, amount: float, interest_rate: float):
        """
        A mortgage for a property.

        Parameters
        ----------
        term_months : int
            The length (term) of the mortgage, in months. Typically 360 (12 * 30) for a 30-year mortgage.
        amount : float
            The initial amount of the loan.
        interest_rate : float
            The interest rate on the principal.
        """
        self.term_months: Final[int] = term_months
        self.amount: Final[float] = amount
        self.interest_rate: Final[float] = interest_rate
        self._principal_paid: float = 0.0

    def monthly_payment(self, month: int) -> Mortgage.Payment:
        """
        The monthly payment on the principal and interest.

        Parameters
        ----------
        month : int
            The month number, between 1 and `self.term_months`.

        Returns
        -------
        Mortgage.Payment
            The interest and principal payments for the given month.
        """
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
        """
        The amount of principal left on the loan.
        """
        return self.amount - self._principal_paid

    def pay_principal(self, amount: float) -> None:
        """
        Adds `amount` to the total principal paid.

        Parameters
        ----------
        amount : float
            The principal to pay.
        """
        self._principal_paid += amount


@dataclass
class CashFlow(object):
    """
    Represents cash flow, either in our out of your pocket.

    Parameters
    ----------
    cash_in: float = 0.0
    cash_out: float = 0.0
    """

    cash_in: float = 0.0
    cash_out: float = 0.0

    @property
    def net(self) -> float:
        """
        The net cash flow: `cash_in - cash_out`.

        Returns
        -------
        float
            Net cash flow.
        """
        return self.cash_in - self.cash_out

    def __add__(self, other: CashFlow) -> CashFlow:
        return CashFlow(
            cash_in=self.cash_in + other.cash_in,
            cash_out=self.cash_out + other.cash_out,
        )


class SimulatorInterface(ABC):
    def __init__(self, property: Property, mortgage: Mortgage, holding_period_months: int):
        """
        Defines an interface for sequentially running through the events that occur throughout
        the propety holding period (from when you buy to when you sell).

        Parameters
        ----------
        property : Property
            The property to simulate.
        mortgage : Mortgage
            The loan taken out on the property.
        holding_period_months : int
            The number of months between purchase and sale of the property.
        """
        self.property = property
        self.mortgage = mortgage
        self.holding_period_months = holding_period_months
        self.down_payment = self.property.purchase_price - self.mortgage.amount
        self.reset()

    @property
    def loan_to_value(self) -> float:
        """
        The loan-to-value ratio at the current point in the simulation, defined as:
        `self.mortgage.balance / self.property.taxable_value`

        Returns
        -------
        float
            The LTV.
        """
        return self.mortgage.balance / self.property.taxable_value

    @property
    def equity(self) -> float:
        """
        Your owner's equity in the property at the current point in the simulation,
        as defined by:
        `self.property.taxable_value - self.mortgage.balance`

        Returns
        -------
        float
            The equity amount.
        """
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
        """
        Resets the simulation to its initial state.
        """
        self.month = 0
        self.mortgage._principal_paid = 0.0
        self.property.taxable_value = self.property.purchase_price
        self._cash_flows: List[CashFlow] = []

    @property
    def cash_flows(self) -> pd.DataFrame:
        """
        The cash flows for every step in the simulation.

        Returns
        -------
        pd.DataFrame
            A dataframe of cashflows, with columns:
                - month: int
                - cash_in: float
                - cash_out: float
        """
        cash_flows = pd.DataFrame.from_records(
            [{"month": month, **asdict(cash_flow)} for month, cash_flow in enumerate(self)]
        )
        cash_flows["net"] = cash_flows["cash_in"] - cash_flows["cash_out"]
        return cash_flows

    @property
    def annual_cash_flows(self) -> pd.DataFrame:
        """
        Cash flows aggregated yearly. See `self.cash_flows`.
        """
        cash_flows = self.cash_flows
        annual_cash_flows = cash_flows.groupby(cash_flows.index // 12).sum()
        return annual_cash_flows

    @property
    def cash_on_cash_return(self) -> pd.Series:
        """
        The cash-on-cash return, by year.

        Returns
        -------
        pd.Series
            Cash-on-cash return. The index represents the year number.
        """
        annual_cash_flows = self.annual_cash_flows
        cash_on_cash_return = annual_cash_flows["net"] / annual_cash_flows["cash_out"]
        cash_on_cash_return.name = "cash_on_cash_return"
        cash_on_cash_return.index.name = "year"
        return cash_on_cash_return

    @property
    def irr(self) -> float:
        """
        The annual internal rate of return of the annual cash flows.
        """
        annual_cash_flows = self.annual_cash_flows
        irr: float = npf.irr(annual_cash_flows["net"].values)
        return irr

    @abstractmethod
    def on_purchase(self) -> CashFlow:
        """
        Records the events and cash flows incurred when the property is purchased. Typically,
        this is just the down payment as cash out.

        Returns
        -------
        CashFlow
        """
        pass

    @abstractmethod
    def on_month_begin(self) -> CashFlow:
        """
        Records the events and cash flows incurred every month. Typically, this is
        just rents being received as cash in.

        Returns
        -------
        CashFlow
        """
        pass

    @abstractmethod
    def on_month_end(self) -> CashFlow:
        """
        Records the events and cash flows incurred at the end of every month. Typically,
        mortgage payments, maintanence expenses, and utility bills you're liable for as cash out.

        Returns
        -------
        CashFlow
        """
        pass

    def on_year_end(self) -> CashFlow:
        """
        Records the events and cash flows incurred at the end of the year. Typically,
        this is property tax payment and an adjustment to the property's assessed and taxable values.

        Returns
        -------
        CashFlow
        """
        return CashFlow()

    @abstractmethod
    def on_sale(self) -> CashFlow:
        """
        Records the events and cash flows incurred at the sale of the property at the end of the
        holding period. Typically, cash in from the sale, and cash out for seller credits and realtor
        commissions.

        Returns
        -------
        CashFlow
        """
        pass


@dataclass
class IncomeTax(object):
    marginal_rate: float

    def taxable_income():
        pass

    def liability(
        self,
        net_income: float,
    ) -> float:
        return self.taxable_income * self.marginal_rate


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
