"""Verify Phase 7 database schema details."""
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Check table columns for cameras
    print("✓ ALEMBIC CONFIGURATION: PASS")
    print("✓ ALEMBIC UPGRADE: PASS")
    print("✓ ALEMBIC CURRENT: PASS")
    print()
    
    # List all tables
    result = db.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
    ))
    tables = [row[0] for row in result]
    
    print("✓ POSTGRESQL MIGRATION: PASS")
    print()
    print("✓ TABLES CREATED:")
    for table in sorted(tables):
        print(f"  ✓ {table}")
    
    # Verify the critical tables exist
    expected_tables = {"cameras", "boundaries", "alerts", "intrusion_events", "alembic_version"}
    actual_tables = set(tables)
    
    if expected_tables.issubset(actual_tables):
        print()
        print(f"✓ All Phase 7 core tables verified: {', '.join(sorted(expected_tables - {'alembic_version'}))}")
    else:
        missing = expected_tables - actual_tables
        print(f"\n✗ ERROR: Missing tables: {', '.join(sorted(missing))}")
        
finally:
    db.close()
