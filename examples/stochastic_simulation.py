from copy import deepcopy
from multiprocessing.pool import Pool

import matplotlib.pyplot as plt
import seaborn as sns

from mortgage_mage.simulation import Mortgage, Property, StochasticSimulator


def get_irr(sim: StochasticSimulator) -> float:
    irr = sim.irr
    sim.reset()
    return irr


def create_sim(ltv: float) -> StochasticSimulator:
    property = Property(
        purchase_price=394_900, tax_rate=0.019, annual_insurance_cost=3_000, taxable_value=394_900, market_value=394_900
    )
    mortgage = Mortgage(term_months=360, amount=property.purchase_price * ltv, interest_rate=0.0275)
    simulator = StochasticSimulator(property=property, mortgage=mortgage, holding_period_months=60)
    return simulator


def main():
    with Pool() as pool:
        irr80 = pool.map(get_irr, (create_sim(ltv=0.8) for _ in range(1000)))
        irr95 = pool.map(get_irr, (create_sim(ltv=0.95) for _ in range(1000)))
    sns.kdeplot(irr80, label="LTV 80%")
    sns.kdeplot(irr95, label="LTV 95%")
    plt.xlabel("IRR")
    plt.legend()
    plt.savefig("IRR.png", bbox_inches="tight")


if __name__ == "__main__":
    main()
