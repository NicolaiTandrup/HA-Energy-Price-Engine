# First setup

Back up your development Home Assistant, install beta.6 using the
[HACS procedure](HACS_DISTRIBUTION.md), restart HA and reload the browser/app.
Existing users configure their existing site; no deletion/recreation is needed.
Tested cores: 2026.10.3 and 2026.10.4. Hardware performance remains your acceptance check.

You need an installed **official Nord Pool** entry, your actual grid product/class
and your supplier's actual per-kWh markup/VAT convention. Fixed subscriptions are
not marginal costs. No private agreement or heating eligibility is guessed.

Three stages: **source → grid → markup**. Select Radius C only if it is your product.
Enter fractional **øre/kWh**, using a point or comma, and indicate whether the amount
includes VAT. Save confirms your actual agreement. Leave markup blank if unknown;
an existing rate is kept. No dates, monthly fees or product selection are required.
Verified public national defaults are automatic within their effective periods.

Each accepted page is saved. Close/reopen Configure to resume. Review is already
saved; click components to revisit them. Native forms cannot save unsubmitted typing
and have no separate per-page Back button. Avoid simultaneous edits of one site.

New current values start next complete quarter, open-ended until changed, preserving
historical prices and future scheduled overrides. A new site's initial day can have
only remaining-day final coverage. Full-day API queries still need all that day's
quarters. Tomorrow may not yet be published. Raw coverage and final readiness differ.

Final prices opens Diagnostics and shows the selected current/future stored calculation.
An optional cost estimate takes one kWh value per consecutive quarter and a planned/
measured designation. Unknown energy/prices are not zero; all prices must be verified.
Provisional prices support visualization only and never make the CM API READY.

Follow the [illustrated guide](WIZARD_GUIDE.md) and [acceptance checklist](BETA_ACCEPTANCE.md).
Your real agreement, sources, bill, physical mobile experience and Raspberry Pi
performance are not established by synthetic software tests.
