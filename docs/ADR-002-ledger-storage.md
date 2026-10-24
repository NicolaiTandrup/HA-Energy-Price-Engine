# ADR-002: transactional ledger persistence for the beta candidate

Accepted for beta development, 2026-10-24. Extends ADR-001 without changing API v1.

The preview rewrote its entire per-site JSON history on each changed publication.
A synthetic one-year baseline (35,136 quarters including the next-day append) on
this cloud host took 1.68 s to append 96 rows and stored 69,484,739 bytes. That is
unnecessary rewrite/serialization work and grows with permanent history.

Use SQLite from Python's standard library, one database per config entry under
`.storage/ha_energy_price_engine.<entry-id>.ledger.sqlite3`. Schema version 1 stores
quarter rows, monotonic site revisions, batch signatures, compressed deduplicated
provenance and append-only correction audit. All database operations run in HA's
executor. A single FULL-synchronous rollback-journal transaction commits changed
quarters, audit and revision together; no WAL sidecars are needed for backup.
Prices and provenance have checksums; SQLite integrity checks plus those checksums
reject corrupted state. Stale runtime writers cannot overwrite a later revision.

The tested pricing calculation and immutable public records are retained. The memory
index remains synchronous/read-only for API v1 compatibility with EV #15/#16. Final
amount lookups never fetch, calculate, write or access the database. Avoid full-history
JSON validation, price-key hashing and redundant planning objects on every append.
Already verified immutable rows need only boundary ordering checks when merged.
Read-time construction of a PriceSlot copies a stored amount and is not tariff math.

Valid HA Store v1 ledgers import once, atomically, after record verification. Original
JSON files remain untouched. Repeated startup prefers the committed SQLite state and
never reimports older data. Invalid/corrupt ledgers fail closed and block new writes;
no empty replacement silently discards referenced history. Old writers/config versions
are rejected; downgrade requires a coherent full configuration/code/storage backup.
There is no automatic retention pruning of authoritative referenced prices.

Native Options can create a verified SQLite snapshot. `tools/ledger_backup.py`
inspects/backups locally; restore requires explicit offline confirmation, validates
the snapshot, and preserves original destination bytes in a separate file. Compare
backup revisions with consumer history before restore: a backup cannot recreate
changes made after it. Never run the restore tool on a running or unapproved live HA.

Actual disk tests cover legacy import/idempotency, an abruptly exited uncommitted
writer, mid-transaction I/O failure, stale-writer rejection, corrupt database/amount/
provenance, and verified offline restore. No production installation was accessed.
See PERFORMANCE.md for measured synthetic resource costs and honest hardware limits.
