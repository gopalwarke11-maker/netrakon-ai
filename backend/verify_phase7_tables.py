"""Verify Phase 7 database tables were created successfully."""
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    result = db.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"
    ))
    tables = [row[0] for row in result]
    
    print("✓ POSTGRESQL MIGRATION: Tables in netrakon database:")
    for table in tables:
        print(f"  ✓ {table}")
    
    expected_tables = {"alembic_version", "cameras", "boundaries", "alerts", "intrusions"}
    actual_tables = set(tables)
    
    if expected_tables.issubset(actual_tables):
        print(f"\n✓ All expected tables created: {', '.join(sorted(expected_tables))}")
    else:
        missing = expected_tables - actual_tables
        print(f"\n✗ Missing tables: {', '.join(sorted(missing))}")
        
finally:
    db.close()
