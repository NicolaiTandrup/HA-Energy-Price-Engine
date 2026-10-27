# First setup

Install the published beta using the exact [HACS procedure](HACS_DISTRIBUTION.md),
restart HA and follow the [native wizard guide](WIZARD_GUIDE.md). Existing users
configure their existing site; a separate Add integration creates another site.
Back up before upgrading. The tested cores are 2026.10.3 and 2026.10.4; real hardware
capacity and your bill remain acceptance checks.

You need:

- Your configured **official Home Assistant Nord Pool** entry and actual area.
- Your actual grid product, e.g. Radius C if applicable.
- Your electricity supplier's per-kWh markup, unit, VAT convention and effective
  dates from a bill or contract. Supplier selection alone supplies no amount.
- Verified national rates for periods outside the documented dated baselines.

A fixed subscription is not a marginal kWh price. A missing supplier markup never
becomes zero. If you cannot verify it yet, finish explicitly incomplete or approve
a clearly labelled visualization estimate. Estimates are excluded from verified
history and the authoritative API and must never control charging.

One entry is one independently configurable site. Set a readable name and keep its
stable ID when editing. Preferred display is øre/kWh; stored prices and existing
canonical entities remain DKK/kWh including VAT. Official source input is fixed
DKK/MWh excluding VAT, independent of display.

Review compares Today/Tomorrow and links to missing components. Save & verify
waits for normal runtime persistence and checks today's complete verified prices.
A saved-incomplete form asks for corrections; it is not complete setup success.
Raw prices remain observable separately. Tomorrow may not yet be published.

After saving, inspect final status, raw coverage and a stored quarter breakdown,
then restart and confirm history/revisions. Run the
[acceptance checklist](BETA_ACCEPTANCE.md). Isolated simulations do not verify
your credentials, invoice, provider availability or Raspberry Pi performance.
