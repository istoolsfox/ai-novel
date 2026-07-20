import argparse
import json
import sys

from .database import init_db
from .key_rotation import key_rotation_history, restore_previous_master_key, rotate_master_key
from .migration_service import apply_pending_migrations, migration_plan, migration_runs, migration_status, rollback_upgrade


def print_json(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="AI Novel database migration and master-key maintenance")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    commands.add_parser("plan")
    commands.add_parser("runs")
    commands.add_parser("apply")

    rollback = commands.add_parser("rollback")
    rollback.add_argument("backup_id")

    rotate = commands.add_parser("rotate-key")
    rotate.add_argument("--new-key", default="")

    restore_key = commands.add_parser("restore-key")
    restore_key.add_argument("rotation_id")
    commands.add_parser("key-history")
    return root


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    init_db()
    try:
        if args.command == "status":
            print_json(migration_status())
        elif args.command == "plan":
            print_json(migration_plan())
        elif args.command == "runs":
            print_json(migration_runs())
        elif args.command == "apply":
            print_json(apply_pending_migrations(confirmation="APPLY"))
        elif args.command == "rollback":
            print_json(rollback_upgrade(args.backup_id, confirmation="ROLLBACK"))
        elif args.command == "rotate-key":
            print_json(rotate_master_key(confirmation="ROTATE", new_master_key=args.new_key))
        elif args.command == "restore-key":
            print_json(restore_previous_master_key(args.rotation_id, confirmation="RESTORE_KEY"))
        elif args.command == "key-history":
            print_json(key_rotation_history())
        return 0
    except ValueError as exc:
        print_json({"status": "error", "error": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
