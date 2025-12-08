# Path and File Name : /home/ransomeye/rebuild/ransomeye_core/bin/run_migrations.py
# Author: nXxBku0CKFAJCBN3X1g3bQk7OxYQylg8CMw1iGsq7gU
# Details of functionality of this file: Database migration runner that creates initial schema and test tables

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_env():
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent / "config" / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

def get_db_connection_string():
    """Get database connection string from environment."""
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_name = os.environ.get('DB_NAME', 'ransomeye')
    db_user = os.environ.get('DB_USER', 'gagan')
    db_pass = os.environ.get('DB_PASS', 'gagan')
    
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

def create_database_if_not_exists(connection_string):
    """Create database if it doesn't exist."""
    # Parse connection string to get database name
    db_name = os.environ.get('DB_NAME', 'ransomeye')
    db_host = os.environ.get('DB_HOST', 'localhost')
    db_port = os.environ.get('DB_PORT', '5432')
    db_user = os.environ.get('DB_USER', 'gagan')
    db_pass = os.environ.get('DB_PASS', 'gagan')
    
    # Connect to postgres database to create target database
    admin_conn_str = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/postgres"
    try:
        admin_engine = create_engine(admin_conn_str, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            result = conn.execute(text(
                f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
            ))
            if result.fetchone() is None:
                logger.info(f"Creating database '{db_name}'...")
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                logger.info(f"Database '{db_name}' created successfully")
            else:
                logger.info(f"Database '{db_name}' already exists")
        admin_engine.dispose()
    except Exception as e:
        logger.warning(f"Could not create database (may already exist or insufficient permissions): {e}")

def run_migrations():
    """Run database migrations."""
    load_env()
    
    connection_string = get_db_connection_string()
    logger.info(f"Connecting to database: {connection_string.split('@')[1] if '@' in connection_string else '***'}")
    
    # Try to create database if it doesn't exist
    create_database_if_not_exists(connection_string)
    
    try:
        engine = create_engine(connection_string, echo=False)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            logger.info(f"Connected to PostgreSQL: {version.split(',')[0]}")
        
        # Create migrations table
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """))
            conn.commit()
            logger.info("Schema migrations table created/verified")
        
        # Create test table to verify schema creation
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ransomeye_core_test (
                    id SERIAL PRIMARY KEY,
                    test_name VARCHAR(255) NOT NULL,
                    test_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()
            logger.info("Test table 'ransomeye_core_test' created/verified")
        
        # Insert test record
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO ransomeye_core_test (test_name, test_value)
                VALUES ('migration_test', 'Database connectivity and schema creation verified')
                ON CONFLICT DO NOTHING
            """))
            conn.commit()
            logger.info("Test record inserted")
        
        # Record migration
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO schema_migrations (version, description)
                VALUES ('001_initial_schema', 'Initial schema creation with test table')
                ON CONFLICT (version) DO NOTHING
            """))
            conn.commit()
            logger.info("Migration recorded in schema_migrations")
        
        # Verify tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Database contains {len(tables)} tables: {', '.join(tables)}")
        
        engine.dispose()
        logger.info("Migrations completed successfully")
        return True
        
    except OperationalError as e:
        logger.error(f"Database connection error: {e}")
        logger.error("Please ensure PostgreSQL is running and credentials are correct")
        return False
    except Exception as e:
        logger.error(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)

