# mortgage_mage

Input distributions:

- Rental revenue
- Property tax rate
- Property appreciation/depreciation rate

We'll also need:
A mortgage rates function that relates interest rate with loan-to-value and loan amount, accounting for PMI and second lien.

## Notes

The median interest rate (computed from `rate_scraper.get_rate_distribution`) isn't very sensitive to changes in LTV.
