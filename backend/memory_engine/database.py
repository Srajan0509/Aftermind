import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import memory_config

logger = logging.getLogger("memory_engine.database")

db_url = memory_config.DATABASE_URL

# Adjust sqlite URL or postgres prefix if needed
connect_args = {}
if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif db_url.startswith("postgres://"):
    # SQLAlchemy requires postgresql:// instead of postgres://
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """
    Initializes database tables.
    If PostgreSQL is detected, verifies or creates the pgvector extension.
    """
    is_postgres = "postgresql" in str(engine.url)
    if is_postgres:
        try:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("PostgreSQL pgvector extension verified/created.")
        except Exception as e:
            logger.warning(f"Could not initialize pgvector extension: {e}")
            
    # Import models so Base discovers all tables
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Memory Engine tables initialized successfully.")

    # Seed default tenant 'default-org'
    try:
        from .models import Company
        with SessionLocal() as session:
            default_company = session.query(Company).filter(
                (Company.id == "default-org") | (Company.name == "default-org")
            ).first()
            if not default_company:
                session.add(Company(id="default-org", name="default-org", domain="aftermind.internal"))
                session.commit()
                logger.info("Default company tenant 'default-org' initialized.")
    except Exception as e:
        logger.warning(f"Default company seeding check skipped: {e}")


def get_db():
    """FastAPI dependency for yielding database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
