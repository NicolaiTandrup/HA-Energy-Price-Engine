# HACS distribution gate and PAHA02-DEV procedure

**Current status: blocked for normal HACS installation. The beta is not complete
as an owner-installable HACS beta.** Native source and manual ZIPs exist, but HACS
rejects both current default branches. Do not interpret passing validation actions
or ZIP smoke tests as an installation on PAHA02-DEV.

## Verified cause and workflow evidence

Read-only GitHub snapshots on 2026-10-25 (`contracts/hacs-default-branches.json`):

| Repository | Default branch | Recorded tree | Contents |
| --- | --- | --- | --- |
| HA-Energy-Price-Engine | main | `981e48988197bc4fd32bd2e877946db469be2a57` | LICENSE, README.md |
| HA-EV-Charge-Manager | main | `0f0b002b136f2ef2480151dc42797256c5cabe8c` | LICENSE, README.md |

The HACS Custom repositories action extracts owner/repository from the URL, then
registers it without a branch argument. A `/tree/feat/...` suffix is discarded;
entering that URL does not select a development branch. HACS first resolves the
repository version/default branch and requires a real integration tree there.
An unpublished branch ZIP or Actions artifact is not a custom-repository URL.
Do not suggest entering an opaque branch SHA as a normal HACS version.

`tests/test_hacs_workflow.py` runs unchanged pinned upstream HACS code:

- Published HACS 2.0.5: `c0dfd8b44297c3673c21973e2539375a53687a9c`.
- Upstream development: `a15e87ec0d1c82e58f1ddbaf17669d3eaa261eb8`.
- Actual `HacsBase.async_register_repository` reproduces the owner's exact
  `Repository structure for main is not compliant` error for both recorded trees.
- Actual candidate registration, download/archive extraction, update backup,
  uninstall and reinstall paths are exercised in temporary HA directories with
  candidate integration trees, modelling an **approved** default-branch distribution.
  No validator, installer or extraction method is replaced. GitHub metadata,
  tree/content/archive transport is the mocked boundary. Both PE and pinned CM #26
  trees are tested. Native PE install/config/options/reload/removal/recreation is
  additionally tested outside the source checkout.

This is executable HACS backend workflow evidence, not a live authenticated HACS
frontend session or proof that today's unchanged repositories are installable.
PAHA02-DEV's installed HACS version must be recorded during owner acceptance.

## Reviewable distribution choices — none executed

**Recommended:** after review and explicit owner authorization, merge existing PE
PR #7 and the reviewed CM stack ending at #26 into their existing `main` branches.
Keep the PRs, commits and history. No force push or history replacement. Both
roots then contain `custom_components/<domain>/manifest.json`, native flows,
translations, brand assets and `hacs.json`. A HACS custom repository can install
its default branch without publishing a GitHub release. The manifest still labels
it beta; HACS may display the branch/commit instead of a published version.
Authorization to merge is separate from release publication and live cutover.

Alternative, only with explicit approval: change each repository's default branch
to the reviewed beta branch, preserving main untouched. This affects repository-wide
PR targets, documentation links and automation; it is not a local packaging fix.
Record exact before/after settings, freeze the reviewed branch, and provide a
reversion plan. No default-branch setting was changed by this work.

Another separately approved option is a dedicated beta distribution repository
whose default branch contains only the reviewed integration plus provenance,
license, HACS metadata and clear link to the original development PR/commit.
No such repository was created. Maintaining exact provenance/updates then becomes
an additional distribution responsibility; it must not fork tariff ownership.

A release/tag is not created as a workaround. Prerelease-only discovery behavior
must be tested before claiming it fixes initial custom-repository registration.

## Exact PAHA02-DEV steps after the chosen gate is approved and implemented

1. Record the reviewed PE and CM source commits and package hashes, HA OS/core and
   HACS versions; take a complete HA backup. Confirm this is **PAHA02-DEV**, not
   production. Keep CM command execution disabled; source setup grants no control.
2. Confirm both repository default branches now contain the complete reviewed
   native integrations. If HACS still reports the structure error, stop: the
   distribution gate has not been implemented. Do not edit private HA files/YAML.
3. In **HACS → ⋮ → Custom repositories**, enter
   `https://github.com/NicolaiTandrup/HA-Energy-Price-Engine`, choose category
   **Integration**, then **Add**. Use the CM URL
   `https://github.com/NicolaiTandrup/HA-EV-Charge-Manager` similarly when its
   separate distribution gate is satisfied. Do not append `/tree/...`.
4. Open **Energy Price Engine** in HACS, choose **Download** (or **Download again**
   for an existing installation). Select the approved available branch/version;
   without a release use the exposed default branch. Verify the installed commit
   matches the reviewed distribution head. Stop on a mismatch. Do not enable
   unattended updates for this controlled beta pilot.
5. Restart HA through **Settings → System → Restart Home Assistant** if prompted;
   a restart after changing custom integration code is the repeatable procedure.
6. The official **Nord Pool** integration already tested by the owner remains the
   source. Verify its DK2/DKK entry is present under **Settings → Devices & services**.
   There is no requirement to run a legacy HACS Nordpool broker simultaneously.
7. Choose **Add integration → Energy Price Engine**. Set the site name and stable
   site ID. Choose **Official Home Assistant Nord Pool** and select the readable
   installed Nord Pool entry from the dropdown. Confirm DK2, Europe/Copenhagen,
   DKK/MWh spot excluding VAT and VAT fraction 0.25. The real opaque entry ID is
   stored internally; never type/guess an entity ID or modify Python/YAML.
8. Open the PE entry's **Configure / Options**. Configure the actual supplier,
   dated contract markup, Radius tariff class/source or manual bands, Energinet,
   electricity tax and VAT. Review effective dates/locks; **Save changes** applies
   the draft. Unknown components intentionally prevent READY. EWII household
   0.030 ex VAT is only June–September 2026, not an October or summer-house rate.
9. Inspect current/next price, complete-day min/max/average and tomorrow readiness.
   Readiness attributes show chosen source, site, area, currency, resolution,
   verification, last error and next scheduled check. Options → **Inspect a stored
   quarter-hour price** shows amounts, VAT, period, revision and UTC offset.
10. Repeat Add integration for each independent site. In CM select **Energy Price
    Engine**, explicitly map the actual producer entry and site; use the reviewed
    current CM #26 candidate rather than superseded #25 packaging. Keep CM read-only.
11. Run the software and owner acceptance checklist, record actual source data,
    reload/restart persistence, 92/96/100-slot evidence, 00:01/publication behavior,
    Pi RAM/storage/latency and recorded legacy/billing comparisons. A mocked service
    test or cloud benchmark cannot check these boxes for PAHA02-DEV.

## Update, remove/reinstall and rollback

For an approved update, back up first, record source commits, use HACS **Download
again/Update**, restart, then verify site IDs/options/history/revisions and readiness
before letting consumers plan. Do not downgrade code alone across storage schemas.

To remove a site use its Devices & services entry menu → **Delete**. Other sites
continue independently. Authoritative ledgers remain retained; re-adding the same
site ID creates a new entry and never silently attaches another entry's history.
To uninstall integration code, first remove/unload its entries, then HACS **Remove**,
then restart. HACS removes integration files, not an authorization to erase price
history or consumer accounting references. Reinstall through the same HACS procedure.

Actual production cutover is outside this test-installation procedure. Follow
[BETA_ACCEPTANCE.md](BETA_ACCEPTANCE.md), including rollback restoration of the
legacy Nordpool dependency AND all three exact saved Node-RED flows. No HACS test
in this repository connects to an owner's installation or changes repository settings.
