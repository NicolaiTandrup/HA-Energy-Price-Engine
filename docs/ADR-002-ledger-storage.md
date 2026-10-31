# ADR-002: transactional permanent quarter-hour history

Accepted2026-10-24; beta.10 simplifies the producer API to v2 while retaining the
compressed SQLite storage implementation and historical immutability.

The JSON preview rewrote a whole site history on each publication. SQLite stores
changed quarters, monotonic revisions, bounded batch verification signatures,
compressed deduplicated provenance and append-only corrections in one transaction.
A database per config entry isolates sites; FULL synchronous rollback journal avoids
WAL requirements for backup. Disk work runs in HA's executor. Readers use an
immutable memory snapshot only after durable commit, with no SQL or source I/O.

Checksums and SQLite integrity checks reject corrupt rows/blobs/audit. Stale writers
cannot overwrite a newer revision. Started intervals retain their original amounts
and provenance; newly verified historical coverage may be added explicitly, but a
current private rate never silently verifies older missing quarters. Corrections
replace future records and retain exact old revisions. No automatic retention pruning.

Beta.10 removes preview/legacy JSON migration and planning aliases; old config
versions fail without deleting data. Recreate sites explicitly after backup. Historical
release tags preserve their original schemas. Verified backup/explicit offline restore
preserves corrupt originals and requires a coherent config/code/storage rollback.
Practical scale/fault-injection evidence and hardware limits: [PERFORMANCE.md](PERFORMANCE.md).
