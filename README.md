# mortgage_mage

Model leveraged real estate transactions easily with `mortgage_mage`! Helps you answer questions such as:

- What size down payment maximizes my expected IRR?
- What's the highest interest rate I could accept before my NOI is unacceptable?

## Key Features

- Convenient pro-forma framework makes it easy to evaluate investments
- Pulls the latest mortgage interest rate data from multiple market sources
- Computes useful metrics, such as cash-on-cash return and IRR
- Factors in your personal tax situation

## Installation

```bash
pip install git+https://github.com/schmidt-jake/mortgage_mage.git
```

## Getting Started

TBD

## Feature Roadmap

1. Tax — record tax deductible transactions, compute final tax liability given marginal income tax bracket, compute metrics on after-tax P&L
1. Stochastic modeling — create an MCMC interface to model the variation of P&L
1. Data layer — enhance the mortgage market data sourcing, add sources for rental market and housing market

## Notes

The median interest rate (computed from `rate_scraper.get_rate_distribution`) isn't very sensitive to changes in LTV.

Input distributions:

- Rental revenue
- Property tax rate
- Property appreciation/depreciation rate

We'll also need:
A mortgage rates function that relates interest rate with loan-to-value and loan amount, accounting for PMI and second lien.
