"""Local ledger inspection/backup/offline restore. No HTTP or running HA access."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custom_components.ha_energy_price_engine.ledger import (
    backup_ledger,
    export_recorded_range,
    inspect_ledger,
    restore_ledger,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("inspect", "backup", "restore", "export"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument(
        "--confirm-offline",
        action="store_true",
        help="For restore: HA is stopped and backup revisions/consumer references have been reviewed",
    )
    parser.add_argument("--site")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    try:
        if args.operation == "inspect":
            result = inspect_ledger(args.source)
        elif args.operation == "export":
            if not all((args.site, args.start, args.end)):
                parser.error("export requires --site --start --end")
            result = export_recorded_range(
                args.source,
                args.site,
                datetime.fromisoformat(args.start),
                datetime.fromisoformat(args.end),
            )
        elif args.destination is None:
            parser.error("backup/restore require a separate destination")
        elif args.operation == "backup":
            result = {"backup": backup_ledger(args.source, args.destination)}
        else:
            result = restore_ledger(
                args.source, args.destination, confirm_offline=args.confirm_offline
            )
    except (OSError, ValueError) as err:
        parser.exit(1, str(err) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
