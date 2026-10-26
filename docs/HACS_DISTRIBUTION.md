# Install Energy Price Engine beta.1 with HACS

Repository: **NicolaiTandrup/HA-Energy-Price-Engine**  
HACS category: **Integration**  
HACS and native integration name: **Energy Price Engine**  
Release: **v0.1.0-beta.1**, manifest version `0.1.0-beta.1`  
[Public prerelease](https://github.com/NicolaiTandrup/HA-Energy-Price-Engine/releases/tag/v0.1.0-beta.1)

The owner authorized merging PE PR #7 and publishing this PE prerelease on
2026-10-26. This does not authorize CM publication, a stable release, production
installation, Node-RED changes or vehicle/charger commands. Publication and exact
source/asset validation receipts are recorded on the public release and PR #7;
check that the release is published, marked **Pre-release**, and not a draft.

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
   Enable **Show beta versions** if beta.1 is hidden. Choose **v0.1.0-beta.1** in
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
7. Choose **Settings → Devices & services → Add integration → Energy Price Engine**.
   Enter a readable site name and stable lowercase site ID, for example `dev_house`.
   Select **Official Home Assistant Nord Pool**, then select the installed entry by
   its readable name in the dropdown. PE stores its actual opaque config-entry ID;
   never type an entity name/ID or edit integration code to find it.
8. Confirm **DK2**, **Europe/Copenhagen**, input **DKK/MWh**, **spot excluding VAT**,
   and VAT fraction **0.25**. PE requests DKK and normalizes MWh to kWh once.
9. Open the new entry's **Configure / Options**. Enter verified, dated supplier,
   grid/Radius class, Energinet, electricity-tax and VAT components. Configure locks,
   manual hourly bands or fallback as appropriate; use **Save changes** to commit
   the draft. See [BETA_SETUP.md](BETA_SETUP.md) for each native editor.
   Missing/unverified current rates intentionally prevent READY; never enter an
   invented zero. The historical household EWII .030 DKK/kWh ex-VAT markup applies
   only June–September 2026, not October or another site.
10. Inspect the site's seven entities: current and next-quarter final price,
    today's complete minimum/maximum/average, readiness and tomorrow readiness.
    Readiness attributes show source/area/currency/resolution, counts, verification,
    last error and next scheduled check. Options → **Inspect a stored quarter-hour
    price** shows original components, VAT, sources, effective periods and revision.
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
It checks tag/source identity and SHA-256/file provenance, then reruns those real
HACS methods using the downloaded public bytes and native installation/configuration
outside the source tree. This is an isolated HACS backend/native HA harness, not
an authenticated session on PAHA02-DEV. See the release's verification receipt.

```sh
.venv-ha-current/bin/python tools/verify_public_release.py \
  --expected-commit THE_VALIDATED_RELEASE_COMMIT --output /tmp/pe-public-beta1
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
