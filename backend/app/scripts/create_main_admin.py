"""CLI bootstrap script to create or update the initial MAIN_ADMIN user for NETRAKON AI.

Usage:
  python -m app.scripts.create_main_admin [--name "Admin Name"] [--email "admin@netrakon.ai"] [--password "SecretPass123"]
"""

import argparse
import getpass
import sys
import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password, normalize_email, UserRole
from app.db.models import UserRecord
from app.db.session import SessionLocal, engine


def create_main_admin(name: str | None = None, email: str | None = None, password: str | None = None) -> bool:
    if engine is None:
        print("ERROR: DATABASE_URL is required. Configure PostgreSQL environment variable before running.")
        sys.exit(1)

    print("==================================================")
    print("NETRAKON AI — MAIN ADMIN BOOTSTRAP")
    print("==================================================")

    # 1. Interactive prompts if arguments not provided
    if not name:
        name = input("Enter Full Name (default: Main Admin): ").strip()
    if not name:
        name = "Main Admin"

    if not email:
        email = input("Enter Email Address: ").strip()
    
    normalized_email = normalize_email(email)
    if not normalized_email or "@" not in normalized_email:
        print("ERROR: Invalid email address.")
        return False

    if not password:
        password = getpass.getpass("Enter Password: ")
        confirm_password = getpass.getpass("Confirm Password: ")
        if password != confirm_password:
            print("ERROR: Passwords do not match.")
            return False

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters long.")
        return False

    # 2. Check database for existing email
    with SessionLocal() as db:
        pw_hash = hash_password(password)
        existing_user = db.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
        
        if existing_user:
            existing_user.password_hash = pw_hash
            existing_user.role = UserRole.MAIN_ADMIN.value
            existing_user.is_active = True
            existing_user.updated_at = datetime.now(timezone.utc)
            db.commit()

            print(f"SUCCESS: Existing account for '{normalized_email}' updated to MAIN_ADMIN!")
            print(f"User ID: {existing_user.id}")
            print(f"Name   : {existing_user.name}")
            print(f"Email  : {normalized_email}")
            print(f"Role   : {UserRole.MAIN_ADMIN.value}")
            print(f"Active : True")
            print("Action : UPDATED")
            print("==================================================")
            return True

        # 3. Securely hash password and persist new MAIN_ADMIN user
        user_id = f"usr_{uuid.uuid4().hex[:16]}"
        new_admin = UserRecord(
            id=user_id,
            name=name,
            email=normalized_email,
            password_hash=pw_hash,
            role=UserRole.MAIN_ADMIN.value,
            is_active=True,
        )
        db.add(new_admin)
        db.commit()

        print(f"SUCCESS: MAIN_ADMIN user created successfully!")
        print(f"User ID: {user_id}")
        print(f"Name   : {name}")
        print(f"Email  : {normalized_email}")
        print(f"Role   : {UserRole.MAIN_ADMIN.value}")
        print(f"Active : True")
        print("Action : CREATED")
        print("==================================================")
        return True


def main():
    parser = argparse.ArgumentParser(description="Create or update initial MAIN_ADMIN account for NETRAKON AI.")
    parser.add_argument("--name", type=str, help="Full name of Main Admin")
    parser.add_argument("--email", type=str, help="Email address of Main Admin")
    parser.add_argument("--password", type=str, help="Password for Main Admin")
    args = parser.parse_args()

    create_main_admin(name=args.name, email=args.email, password=args.password)


if __name__ == "__main__":
    main()

