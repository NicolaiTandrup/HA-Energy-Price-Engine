# SQLite performance and recovery

The compressed, deduplicated SQLite ledger from the original validated work is
retained. Each entry owns `.storage/ha_energy_price_engine.<entry-id>.ledger.sqlite3`.
Only changed rows and revision audit enter an atomic FULL-synchronous transaction;
immutable past rows are not rewritten. A memory index serves reads, without SQL,
provider requests or tariff recomposition. All SQLite work uses HA's executor.

Synthetic measurements on this cloud Linux x86_64 host, Python3.14.8/HA 2026.10.3:

| Test | Stored quarters | Initial import | Append 96 | Reload |96-row memory read |Disk |
|---|---:|---:|---:|---:|---:|---:|
|beta.10,1year|35,136|7.81s|0.043s|1.71s|10.2µs|18.8MB|
|beta.10,5years|175,296|27.53s|0.136s|4.56s|5.3µs|74.2MB|

Peak process RSS was246/684 MiB approximately (reported raw KiB in JSON); this includes
HA, synthetic inputs, memory indexes and Python allocations, not SQLite alone. All
history is retained and indexed in memory. Large installations need storage/RAM
acceptance. **Cloud benchmarks do not establish Raspberry Pi performance.** The
original JSON preview's1year96-row append was 1.68 s and 69.5 MB; the important preserved
improvement is bounded changed-row persistence rather than rewriting all history.
Do not treat different-host/timing runs as a hardware guarantee.

Exact new measurements: [1year](benchmarks/beta10-sqlite-1year.json),
[5years](benchmarks/beta10-sqlite-5years.json). Run
`python tools/benchmark_ledger.py --years 1 --output /tmp/pe-benchmark.json`
with the locked development environment. Inputs/long date validity are explicitly
fictional benchmark fixtures, not contract defaults. The test never connects to HA.

Recovery regressions use real disk: terminated uncommitted writer, mid-transaction
SQLite failure, stale concurrent writer, corrupt bytes/amount/provenance, verified
backup/offline restore, permanent historical freeze and three independent year-scale
site histories. Readers see the old immutable snapshot until the commit succeeds.
No automatic pruning or replacement of corrupt history occurs. Corruption prevents
new writes and future READY; restore requires explicit offline confirmation.

Back up a selected stopped development instance with:

```sh
python tools/ledger_backup.py inspect /path/to/site.ledger.sqlite3
python tools/ledger_backup.py backup /path/to/site.ledger.sqlite3 /backup/new.sqlite3
python tools/ledger_backup.py restore /backup/new.sqlite3 /path/to/site.ledger.sqlite3 --confirm-offline
```

The backup must be new, not an existing file. Restore validates checksums/integrity
and preserves original destination bytes separately. Stop HA first and retain a
full coherent config/code/storage backup. A snapshot cannot recreate later revisions.
Do not run these examples against unapproved production HA. Beta.10 removes the
old JSON-history importer; old beta configurations require explicit development
reset/recreation. See [installation/reset](HACS_DISTRIBUTION.md).
