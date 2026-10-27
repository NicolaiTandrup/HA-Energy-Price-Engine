# Measured synthetic ledger resource use

These are **cloud Linux x86_64 measurements, not Raspberry Pi measurements**. The
locked Python 3.14.8 environment runs a fresh isolated HA object and temporary files;
no provider/network/production access. Reproduce with:

```sh
.venv/bin/python tools/benchmark_ledger.py --years 1 --output /tmp/pe-1year.json
.venv/bin/python tools/benchmark_ledger.py --years 5 --output /tmp/pe-5year.json
```

| Backend / synthetic history | Rows | Storage bytes | Append 96 rows | Reload | 96-row lookup mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| Preview JSON / one year | 35,136 | 69,484,739 | 1.675 s | 0.952 s | 5.58 µs |
| Beta SQLite / one year | 35,136 | 18,239,488 | 0.030 s | 0.844 s | 5.64 µs |
| Beta SQLite / five years | 175,296 | 69,611,520 | 0.115 s | 4.519 s | 5.83 µs |

Raw reports are in `docs/benchmarks`. Peak whole-process RSS (including HA imports,
bulk synthetic inputs and both original/restored engines) was about 424 MiB for the
one-year JSON baseline, 238 MiB for one-year SQLite, 647 MiB for five-year SQLite.
These are benchmark peaks, not steady-state per-site RAM budgets or Pi predictions.
The fixture cycles 10,000 spot values under an explicitly fictional fixed component
schedule; real source/contract diversity changes compression, provenance and audit
size. Five years of one bulk synthetic write took about 26 s; normal publication
is a 96-row daily batch, not a five-year recomposition. Checksums and SQLite work run
in the executor; API lookups are indexed in memory.

Practical beta guidance: use a supported 64-bit HA OS installation, reliable storage
and full backups; record HA process RAM, event-loop responsiveness, free space and
source latency during a read-only pilot. More sites and frequent corrections add
memory/audit costs. The beta keeps all immutable history in RAM for synchronous
API v1 compatibility; it has no arbitrary site cap but cannot promise unlimited
history/sites on every Raspberry Pi. Native hardware commissioning and multi-site
Pi measurements remain owner-run acceptance gates, not claimed completed tests.
If limits are reached, design a backward-compatible async historical paging API;
do not silently prune prices referenced by recorded consumer accounting.

Beta.4 repeat (same cloud host class): 35,136 synthetic rows, 18,239,488 bytes,
96-row append 0.0293 s, reload 0.891 s, lookup mean 6.65 µs; process peak RSS
244,264 KiB. [Raw receipt](benchmarks/beta4-sqlite-1year.json). Transactional touched-row
writes and original historical revisions are retained. These cloud results do not
establish Raspberry Pi performance; measure append/recovery on the target hardware.

Beta.5 repeat during concurrent cloud validation: 35,136 rows, 18,239,488 bytes;
96-row append 0.0457s, reload 2.240s, lookup mean 10.06µs; process peak 243,448KiB.
[Raw receipt](benchmarks/beta5-sqlite-1year.json). The original touched-row SQLite
implementation is retained. Load/concurrency affect timings; these remain cloud
measurements and do not establish Raspberry Pi performance. Recovery, revision,
migration and multi-site failure/isolation tests run in both supported core suites.

Beta.6 repeat during concurrent cloud validation: 35,136 rows, 18,239,488 bytes;
96-row append 0.0288 s, reload 1.066 s, lookup mean 5.29 µs; process peak 243,580 KiB.
[Raw receipt](benchmarks/beta6-sqlite-1year.json). Transactional touched-row SQLite
writes remain unchanged. These cloud timings do not establish Raspberry Pi
performance. Both-core suites exercise recovery, migration and revision isolation.

Beta.7 repeat during concurrent cloud validation:35,136 rows,18,239,488 bytes;
96-row append0.0302s,reload1.599s,indexed lookup mean11.51µs,peak243,720KiB.
[Raw receipt](benchmarks/beta7-sqlite-1year.json). Engine/ledger code is unchanged
from beta.6; workload/concurrency affect timings. Cloud benchmarks do not establish
Raspberry Pi performance. Live consumer requests use the loaded index, not SQL or
network calls; the new repeated-read guards reject both connections and recomposition.
