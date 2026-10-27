# Install Energy Price Engine beta.3 with HACS

Repository: **NicolaiTandrup/HA-Energy-Price-Engine**
HACS category: **Integration**
HACS and native integration name: **Energy Price Engine**
Release: **v0.1.0-beta.3**, manifest version `0.1.0-beta.3`
[Public prerelease](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.3)

The owner authorizes beta.3 publication after mandatory checks. Its source is the
validated tag on PR #11's development branch; main stays on the previously approved
beta.1 implementation. HACS uses main for registration and the exact selected beta
tag for download. No main merge, stable release, CM release or live control operation
is included. Confirm the public release is **Pre-release**, not a draft.

## PAHA02-DEV: exact installation procedure

1. Confirm the destination is **PAHA02-DEV**, not PAHA01/production. Record HA OS,
   core and HACS versions and take a full HA backup. The tested core versions are
   2026.10.3 and 2026.10.4, Python 3.14.8. Use supported 64-bit HA OS; cloud tests
   do not establish Raspberry Pi capacity.
2. Open **HACS → ⋮ → Custom repositories**. Enter exactly
   `https://github.com/NicolaiTandrup/HA-Energy-Price-Engine`, choose
   **Integration**, then **Add**. Do not append a branch URL or enter a ZIP URL.
3. Find and open **Energy Price Engine** in HACS. Open **Download** (or the
   repository menu's **Redownload/Download again** for an existing installation).
   Enable **Show beta versions** if beta.3 is hidden. Choose **v0.1.0-beta.3** in
   the available-version selector and download. HACS UI wording can vary by version;
   the required actions are enable beta versions and select this exact release.
   Do not accidentally select the moving `main` development version.
4. If the release is not listed, use HACS repository **Refresh/Update information**
   after enabling beta versions and confirm the public prerelease URL above exists.
   If the structure error persists, check that the exact PE repository/category was
   added. The separate EV Charge Manager repository is not published by this mission.
   Save the actual HACS error/version rather than editing private HA files or YAML.
5. Restart Home Assistant through **Settings → System → Restart Home Assistant**
   after downloading custom integration code. HACS places files under
   `custom_components/ha_energy_price_engine/`; do not create a nested second folder.
6. Under **Settings → Devices & services**, confirm the already tested **official
   Home Assistant Nord Pool** integration for DK2 is present. PE needs no additional
   credentials. Do not install/run a legacy HACS Nordpool broker in parallel for
   acceptance; an old custom component shadowing the official domain is rejected.
7. For a new site choose **Settings → Devices & services → Add integration → Energy
   Price Engine**. For an existing beta.1 site choose **Configure / Options** instead;
   do not delete/recreate it. Stable IDs, references, overrides and SQLite history
   migrate in place to config version 3.
8. Follow the [six-stage wizard](WIZARD_GUIDE.md): site/official Nord Pool, grid,
   supplier, national charges, display, Review. Official input is automatic
   **DKK/MWh excluding VAT**; confirm DK2/Copenhagen where suggested. VAT input is
   **25** for 25%; preferred display defaults to **øre/kWh**.
9. Enter only verified dated rates. The EWII household .030 DKK/kWh ex-VAT fact is
   June–September 2026 only. Use **Continue** to preserve each draft page; unsent
   fields are lost by HA's Close/reload. Final **Save & verify** applies the draft.
   Missing components remain unavailable; saved does not mean READY.
10. Inspect the original seven DKK/readiness entities and five preferred-display
    sensors. Device info shows **0.1.0-beta.3**. Readiness attributes identify missing
    components, affected period, source/error and corrective action. Review →
    **Dated rates / manual overrides → Inspect a stored quarter-hour price** shows
    applied components, VAT, sources, periods and revision.

11. Repeat **Add integration** for additional independent sites. Use explicit
    producer entry/site mapping for any separately approved consumer. PE has no
    charging or vehicle controls and can be meaningfully tested on its own.
12. Reload the entry and restart test HA to verify saved configuration/history.
    Record real source availability, publication/00:01 behavior and Pi resource use
    in the [acceptance checklist](BETA_ACCEPTANCE.md). No isolated test checks these
    PAHA02-DEV observations on the owner's behalf.

## What is independently tested

The mandatory suite runs unchanged published HACS 2.0.5
`c0dfd8b44297c3673c21973e2539375a53687a9c` and pinned upstream
`a15e87ec0d1c82e58f1ddbaf17669d3eaa261eb8` code. It verifies ordinary repository
registration, integration identification, beta visibility, exact release selection,
tag-archive download/extraction, update backup, uninstall and reinstall. GitHub I/O
is the fixture boundary; validator/installer/extraction methods run unchanged.

After publication, `tools/verify_public_release.py` independently downloads actual
public repository/release/tag metadata, source ZIP and all four release assets.
It separately downloads actual main and tag sources (they may differ), checks
main registration structure and exact tag/source identity and SHA-256/file provenance, then reruns those real
HACS methods using the downloaded public bytes and native installation/configuration
outside the source tree. This is an isolated HACS backend/native HA harness, not
an authenticated session on PAHA02-DEV. See the release's verification receipt.

```sh
.venv-ha-current/bin/python tools/verify_public_release.py \
  --expected-commit THE_VALIDATED_RELEASE_COMMIT --output /tmp/pe-public-beta3
```

`BUILD_MANIFEST.json` describes the clean build; its `published: false` means the
builder itself performs no publication. The GitHub release and public verification
receipt separately establish actual prerelease publication.

## Update, remove/reinstall and rollback

For approved updates, back up first, record exact versions, choose the reviewed
release through HACS, restart, then verify site IDs/options/history/revisions and
readiness. Avoid unattended updates during the controlled beta pilot. Downgrading
code alone across storage schemas is unsupported; use a coherent full backup.

To remove a site: its Devices & services entry menu → **Delete**. Other sites stay
independent. Referenced ledgers remain preserved; re-adding the same site ID creates
a new entry and does not silently attach another entry's history. To remove code,
first remove/unload its entries, then HACS **Remove**, then restart. Reinstall by
following the same HACS steps. Do not erase price history or consumer accounting.

Production source/control cutover remains separately approved. Follow
[BETA_ACCEPTANCE.md](BETA_ACCEPTANCE.md); rollback must restore BOTH the legacy
Nordpool dependency and the exact saved Brain, Energy Price Broker and Charger
Optimizer flows. No production/Node-RED/vehicle operations occur in these tools.

## Historical distribution failure

On 2026-10-25 both PE and CM main trees contained only LICENSE/README; recorded
snapshots are retained in `contracts/hacs-default-branches.json` and tests reproduce
that exact HACS rejection. A `/tree/branch` suffix is discarded by HACS's normal add
workflow. PE's authorized main bootstrap resolves its own structure gate; it does
not change, merge or publish EV Charge Manager.

## Beta.3 retest and the short-hash update card

Beta.2 failed owner acceptance. This candidate adds actual Review source/calculation
checks and independent raw source entities; screenshots/tests remain isolated
simulation, not PAHA02-DEV success. Follow [the focused retest](WIZARD_GUIDE.md).

The recorded `installed v0.1.0-beta.2 / latest 56cdb3c` card belongs to HACS. Actual
pinned HACS code reproduces it when **Show beta versions is off** and the repository
has no stable release: its available-version property falls back to main's commit.
Selecting a beta download alone does not prove this subscription flag remains on.
Keep **Show beta versions enabled in HACS's repository controls**, refresh repository
information, then confirm latest is a semantic beta tag. Do not choose main/commits.
Beta.3 sets hide_default_branch metadata; main registration remains compatible.

PE additionally exposes a read-only **Published PE release (update through HACS)**
UpdateEntity. It compares only published semantic tags, follows beta/stable according
to the installed package, filters drafts/commits, and links exact release notes. It
does not install files or change HACS settings. Stable installs never follow beta.
GitHub failure makes that metadata unavailable; it never affects price readiness.
HACS owns its separate card; PE does not monkey-patch it or publish a stable release
to conceal this upstream fallback. If it still shows a hash, record HACS version and
its persisted beta visibility; use the exact release download rather than the hash.
