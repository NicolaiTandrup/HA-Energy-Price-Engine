"""Transactional, compressed SQLite persistence; all disk work runs in HA's executor.

The pricing engine still owns validation/composition and immutable memory indexes.
SQLite changes only touched quarters and commits amounts, revision and audit in one
transaction. No WAL sidecars are required for HA full-backup consistency.
"""

import hashlib
import json
import sqlite3
import zlib
from asyncio import Lock
from contextlib import closing
from pathlib import Path

SCHEMA_VERSION = 1


class LedgerCorruptError(OSError):
    """Never overwrite an unreadable authoritative history with a fresh empty table."""


class LedgerDatabase:
    def __init__(self, hass, entry_id):
        self.hass = hass
        self.path = Path(
            hass.config.path(".storage", f"ha_energy_price_engine.{entry_id}.ledger.sqlite3")
        )
        self.lock = Lock()

    def _connect(self, *, create=False):
        if create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=30)
        try:
            return self._configure(connection, create)
        except BaseException:
            connection.close()
            raise

    def _configure(self, connection, create):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version not in (0, SCHEMA_VERSION):
            connection.close()
            raise LedgerCorruptError(
                "Unsupported ledger schema; use a compatible integration version"
            )
        if version == 0:
            if not create:
                connection.close()
                raise LedgerCorruptError("Ledger has no recognized schema")
            connection.executescript("""
                BEGIN IMMEDIATE;
                CREATE TABLE IF NOT EXISTS blobs (digest TEXT PRIMARY KEY, body BLOB NOT NULL);
                CREATE TABLE IF NOT EXISTS prices (
                    site TEXT NOT NULL, start TEXT NOT NULL, end TEXT NOT NULL,
                    amount REAL NOT NULL, components TEXT NOT NULL REFERENCES blobs(digest),
                    source TEXT NOT NULL REFERENCES blobs(digest), calculated TEXT NOT NULL,
                    revision INTEGER NOT NULL, checksum TEXT NOT NULL, PRIMARY KEY(site,start));
                CREATE TABLE IF NOT EXISTS state (
                    site TEXT PRIMARY KEY, signature TEXT NOT NULL, revision INTEGER NOT NULL,
                    batches TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, site TEXT NOT NULL, body BLOB NOT NULL);
                PRAGMA user_version=1;
                COMMIT;
            """)
        return connection

    @staticmethod
    def _row_checksum(site, start, end, amount, parts, source, calculated, revision):
        normalized_amount = float(amount) if amount else 0.0
        return hashlib.sha256(
            json.dumps(
                [site, start, end, normalized_amount, parts, source, calculated, revision],
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    @staticmethod
    def _blob(connection, value):
        raw = value.encode()
        digest = hashlib.sha256(raw).hexdigest()
        connection.execute("INSERT OR IGNORE INTO blobs VALUES (?,?)", (digest, zlib.compress(raw)))
        return digest

    async def async_load(self, site):
        async with self.lock:
            return await self.hass.async_add_executor_job(self._load, site)

    def _load(self, site):
        if not self.path.exists():
            return None
        try:
            with closing(self._connect()) as connection:
                if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise LedgerCorruptError("SQLite ledger integrity check failed")
                state = connection.execute(
                    "SELECT signature,revision,batches FROM state WHERE site=?", (site,)
                ).fetchone()
                if state is None:
                    return None
                blobs = {}
                for digest, body in connection.execute("SELECT digest,body FROM blobs"):
                    raw = zlib.decompress(body)
                    if hashlib.sha256(raw).hexdigest() != digest:
                        raise LedgerCorruptError("Ledger provenance checksum mismatch")
                    blobs[digest] = raw.decode()
                records = []
                for (
                    start,
                    end,
                    amount,
                    parts,
                    source,
                    calculated,
                    revision,
                    checksum,
                ) in connection.execute(
                    "SELECT start,end,amount,components,source,calculated,revision,checksum FROM prices WHERE site=? ORDER BY start",
                    (site,),
                ):
                    if (
                        self._row_checksum(
                            site, start, end, amount, parts, source, calculated, revision
                        )
                        != checksum
                    ):
                        raise LedgerCorruptError("Ledger price checksum mismatch")
                    records.append(
                        {
                            "site_id": site,
                            "start": start,
                            "end": end,
                            "final_price_incl_vat": amount,
                            "components_json": blobs[parts],
                            "source_json": blobs[source],
                            "calculated_at": calculated,
                            "revision": revision,
                        }
                    )
                audit = [
                    json.loads(zlib.decompress(row[0]))
                    for row in connection.execute(
                        "SELECT body FROM audit WHERE site=? ORDER BY id", (site,)
                    )
                ]
                return {
                    "records": records,
                    "signature": state[0],
                    "revision": state[1],
                    "batch_signatures": json.loads(state[2]),
                    "audit": audit,
                }
        except (sqlite3.DatabaseError, zlib.error, UnicodeError, KeyError, ValueError) as err:
            raise LedgerCorruptError(
                "Unreadable ledger; restore a verified backup before retrying"
            ) from err

    async def async_commit(
        self, site, records, signature, revision, batches, audit, *, import_only=False
    ):
        async with self.lock:
            await self.hass.async_add_executor_job(
                self._commit, site, records, signature, revision, batches, audit, import_only
            )

    def _commit(self, site, records, signature, revision, batches, audit, import_only):
        try:
            connection = self._connect(create=True)
            try:
                connection.execute("BEGIN IMMEDIATE")
                if (
                    import_only
                    and connection.execute("SELECT 1 FROM state WHERE site=?", (site,)).fetchone()
                ):
                    connection.rollback()
                    return
                current = connection.execute(
                    "SELECT revision FROM state WHERE site=?", (site,)
                ).fetchone()
                if not import_only and revision != ((current[0] if current else 0) + 1):
                    raise OSError("Stale ledger writer; reload before retrying")
                for row in records:
                    parts = self._blob(connection, row["components_json"])
                    source = self._blob(connection, row["source_json"])
                    connection.execute(
                        "INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?,?,?)",
                        (
                            site,
                            row["start"],
                            row["end"],
                            row["final_price_incl_vat"],
                            parts,
                            source,
                            row["calculated_at"],
                            row["revision"],
                            self._row_checksum(
                                site,
                                row["start"],
                                row["end"],
                                row["final_price_incl_vat"],
                                parts,
                                source,
                                row["calculated_at"],
                                row["revision"],
                            ),
                        ),
                    )
                for item in audit:
                    connection.execute(
                        "INSERT INTO audit(site,body) VALUES (?,?)",
                        (site, zlib.compress(json.dumps(item, sort_keys=True).encode())),
                    )
                connection.execute(
                    "INSERT OR REPLACE INTO state VALUES (?,?,?,?)",
                    (site, signature, revision, json.dumps(batches, sort_keys=True)),
                )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.close()
        except sqlite3.DatabaseError as err:
            raise OSError("Ledger transaction failed; prior committed prices retained") from err

    async def async_backup(self, destination):
        """Verified offline/owner-requested backup; never changes current prices."""
        async with self.lock:
            return await self.hass.async_add_executor_job(self._backup, Path(destination))

    def _backup(self, destination):
        return backup_ledger(self.path, destination)


def inspect_ledger(path):
    """Verify a backup structurally and against stored row/provenance checksums."""
    path = Path(path)
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as connection:
            if connection.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
                raise LedgerCorruptError("Unsupported backup schema")
            if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise LedgerCorruptError("Backup integrity check failed")
            blobs = set()
            for digest, body in connection.execute("SELECT digest,body FROM blobs"):
                raw = zlib.decompress(body)
                if hashlib.sha256(raw).hexdigest() != digest or not isinstance(
                    json.loads(raw), dict
                ):
                    raise LedgerCorruptError("Backup provenance is invalid")
                blobs.add(digest)
            for (
                site,
                start,
                end,
                amount,
                parts,
                source,
                calculated,
                revision,
                checksum,
            ) in connection.execute("SELECT * FROM prices"):
                if (
                    parts not in blobs
                    or source not in blobs
                    or LedgerDatabase._row_checksum(
                        site, start, end, amount, parts, source, calculated, revision
                    )
                    != checksum
                ):
                    raise LedgerCorruptError("Backup price checksum/reference is invalid")
            sites = {}
            for site, revision in connection.execute("SELECT site,revision FROM state"):
                count, maximum = connection.execute(
                    "SELECT COUNT(*),MAX(revision) FROM prices WHERE site=?", (site,)
                ).fetchone()
                if type(revision) is not int or revision < (maximum or 0):
                    raise LedgerCorruptError("Backup revision is invalid")
                sites[site] = {"revision": revision, "records": count}
            return {"schema_version": SCHEMA_VERSION, "sites": sites, "bytes": path.stat().st_size}
    except (sqlite3.DatabaseError, zlib.error, ValueError, TypeError) as err:
        raise LedgerCorruptError("Backup is unreadable or corrupt") from err


def restore_ledger(backup, destination, *, confirm_offline=False):
    """Explicit offline restore; preserve original bytes for forensic recovery.

    The owner must compare backup revisions with recorded consumer history before
    this operation. Never run this automatically or against a running HA instance.
    """
    import os
    import shutil
    import uuid

    if not confirm_offline:
        raise ValueError("Stop Home Assistant and explicitly confirm an offline restore")
    backup, destination = Path(backup), Path(destination)
    if backup.resolve() == destination.resolve():
        raise ValueError("Backup and destination must differ")
    result = inspect_ledger(backup)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".restore-" + uuid.uuid4().hex)
    shutil.copyfile(backup, temporary)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    preserved = None
    if destination.exists():
        preserved = destination.with_name(destination.name + ".preserved-" + uuid.uuid4().hex)
        shutil.copyfile(destination, preserved)
    os.replace(temporary, destination)
    return {**result, "preserved_original": str(preserved) if preserved else None}


def backup_ledger(source, destination):
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError("Refusing to overwrite an existing ledger backup")
    if not source.exists():
        raise FileNotFoundError("No ledger exists to back up")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with (
            closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)) as original,
            closing(sqlite3.connect(destination)) as snapshot,
        ):
            original.backup(snapshot)
        inspect_ledger(destination)
        return str(destination)
    except sqlite3.DatabaseError as err:
        raise LedgerCorruptError("Ledger backup failed") from err


def export_recorded_range(path, site, start, end):
    """Read an explicitly selected backup for offline comparison, not live readiness."""
    from datetime import UTC

    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Offline export requires aware UTC interval boundaries")
    start, end = start.astimezone(UTC), end.astimezone(UTC)
    if end <= start or start.timestamp() % 900 or end.timestamp() % 900:
        raise ValueError("Offline export requires a positive quarter-aligned range")
    report = inspect_ledger(path)
    if site not in report["sites"]:
        raise ValueError("Selected site is not present in this backup")
    with closing(
        sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    ) as connection:
        slots = [
            {
                "start": a,
                "end": b,
                "final_price_incl_vat": amount,
                "revision": revision,
                "verified_at": json.loads(zlib.decompress(source)).get("verified_at"),
            }
            for a, b, amount, revision, source in connection.execute(
                "SELECT p.start,p.end,p.amount,p.revision,b.body FROM prices p JOIN blobs b ON b.digest=p.source WHERE p.site=? AND p.start>=? AND p.end<=? ORDER BY p.start",
                (site, start.isoformat(), end.isoformat()),
            )
        ]
    return {
        "capture_type": "offline_checked_ledger_backup",
        "site_id": site,
        "currency": "DKK",
        "unit": "DKK/kWh",
        "vat_included": True,
        "slots": slots,
    }
