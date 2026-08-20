"""Import an existing SQLite database into the configured PostgreSQL database.

Usage:
    python -m backend.migrate_sqlite --source backend/zoopet.db --dry-run
    python -m backend.migrate_sqlite --source backend/zoopet.db
"""
import argparse
import os
import shutil
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from . import models
from .database import DATABASE_URL, SessionLocal

TABLES = (
    models.Category.__table__,
    models.Customer.__table__,
    models.Admin.__table__,
    models.SubscriptionPlan.__table__,
    models.Product.__table__,
    models.ProductVariant.__table__,
    models.Order.__table__,
    models.OrderItem.__table__,
    models.Subscription.__table__,
)


def _sqlite_engine(source: Path):
    return create_engine(
        f"sqlite:///{source.resolve()}",
        connect_args={"check_same_thread": False},
    )


def _rows(source_session: Session, table):
    return source_session.execute(table.select()).mappings().all()


def _validate_source(source_engine):
    available = set(inspect(source_engine).get_table_names())
    missing = [table.name for table in TABLES if table.name not in available]
    if missing:
        raise RuntimeError("SQLite database is missing tables: " + ", ".join(missing))


def _reset_sequence(destination, table_name: str):
    destination.execute(
        text(
            "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
            "COALESCE((SELECT MAX(id) FROM " + table_name + "), 1), "
            "(SELECT COUNT(*) > 0 FROM " + table_name + "))"
        ),
        {"table_name": table_name},
    )


def migrate(source: Path, dry_run: bool = False):
    if not source.is_file():
        raise FileNotFoundError(f"SQLite database not found: {source}")
    if DATABASE_URL.startswith("sqlite"):
        raise RuntimeError("Set DATABASE_URL to PostgreSQL before running the importer")

    source_engine = _sqlite_engine(source)
    _validate_source(source_engine)
    source_session = Session(source_engine)
    destination = SessionLocal()
    counts = {}
    try:
        for table in TABLES:
            counts[table.name] = len(_rows(source_session, table))

        if dry_run:
            for table_name, count in counts.items():
                print(f"{table_name}: {count} rows")
            return counts

        with destination.begin():
            for table in TABLES:
                rows = _rows(source_session, table)
                if rows:
                    destination.execute(table.insert(), rows)
            for table in TABLES:
                _reset_sequence(destination, table.name)

        for table_name, count in counts.items():
            print(f"{table_name}: imported {count} rows")
        return counts
    finally:
        source_session.close()
        source_engine.dispose()
        destination.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    backup = args.source.with_suffix(args.source.suffix + ".migration-backup")
    if not args.dry_run and not backup.exists():
        shutil.copy2(args.source, backup)
        print(f"SQLite backup created at {backup}")

    migrate(args.source, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
