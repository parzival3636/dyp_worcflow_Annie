import sys
import os
import argparse

# Ensure repo root is on sys.path for direct script execution
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import SQLModel
from backend.db import engine
from backend.config import settings
import backend.models  # ensure all models are registered in SQLModel metadata


def reset_database(force: bool = False):
    db_url = settings.DATABASE_URL
    print(f"Target Database: {db_url}")

    if not force:
        confirmation = input(
            "WARNING: This will drop and recreate all tables in the database!\n"
            "To confirm, type 'RESET': "
        )
        if confirmation.strip() != "RESET":
            print("Aborted.")
            sys.exit(1)

    print("Dropping all tables...")
    SQLModel.metadata.drop_all(engine)
    print("Creating all tables...")
    SQLModel.metadata.create_all(engine)
    print("Database reset successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset the Pilot database schema.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip interactive confirmation",
    )
    args = parser.parse_args()
    reset_database(force=args.force)
