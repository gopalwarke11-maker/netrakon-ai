#!/usr/bin/env python
"""Check PostgreSQL database state and verify all tables."""
from sqlalchemy import create_engine, text

# Create database engine with correct credentials
engine = create_engine("postgresql://postgres:Parulgopal%40123@localhost:5432/netrakon")

with engine.connect() as conn:
    # Check tables
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result.fetchall()]
    print("✓ Database tables:", ", ".join(tables))
    
    # Check key data
    try:
        result = conn.execute(text("SELECT COUNT(*) FROM cameras"))
        cam_count = result.scalar()
        print(f"✓ Cameras in database: {cam_count}")
        
        result = conn.execute(text("SELECT COUNT(*) FROM boundaries"))
        bnd_count = result.scalar()
        print(f"✓ Boundaries in database: {bnd_count}")
        
        result = conn.execute(text("SELECT COUNT(*) FROM alerts"))
        alt_count = result.scalar()
        print(f"✓ Alerts in database: {alt_count}")
        
        result = conn.execute(text("SELECT COUNT(*) FROM intrusion_events"))
        evt_count = result.scalar()
        print(f"✓ Intrusion events in database: {evt_count}")
        
        result = conn.execute(text("SELECT COUNT(*) FROM behavior_observations"))
        beh_count = result.scalar()
        print(f"✓ Behavior observations in database: {beh_count}")
        
        result = conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
        alb_count = result.scalar()
        print(f"✓ Alembic version records: {alb_count}")
        
        # Show cameras
        result = conn.execute(text("SELECT id, name FROM cameras ORDER BY id"))
        cameras = result.fetchall()
        print(f"\nCameras:")
        for cam_id, name in cameras:
            print(f"  - {cam_id}: {name}")
        
    except Exception as e:
        print(f"✗ Error querying tables: {e}")

print("\n✓ PostgreSQL connection verified")
