import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from .models import Base

# Database configuration
DATABASE_DIR = './'
DATABASE_PATH = DATABASE_DIR / 'database.db'

def get_database_url():
    """Get database URL from environment or default to SQLite"""
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Ensure database directory exists
    DATABASE_DIR.mkdir(exist_ok=True)
    return f"sqlite:///{DATABASE_PATH}"

def create_database_engine():
    """Create and configure database engine"""
    database_url = get_database_url()
    
    # SQLite specific configuration
    if database_url.startswith('sqlite'):
        engine = create_engine(
            database_url,
            poolclass=StaticPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 20,
            },
            echo=False,  # Set to True for SQL logging
        )
    else:
        engine = create_engine(database_url, echo=False)
    
    return engine

# Global engine and session factory
engine = create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise

def init_db():
    """Initialize database with tables"""
    create_tables()