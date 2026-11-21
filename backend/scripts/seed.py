"""Seed the database with realistic UFAZ-flavoured fake data.

    uv run python scripts/seed.py --reset   # wipe schema, migrate, seed

Grows with each slice; today it only rebuilds the schema.
"""

import argparse
import subprocess
import sys


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="drop and rebuild schema")
    args = parser.parse_args()
    if args.reset:
        subprocess.run(
            [sys.executable, "-m", "alembic", "downgrade", "base"], check=True
        )
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    print("seeded (schema only for now)")


if __name__ == "__main__":
    main()
