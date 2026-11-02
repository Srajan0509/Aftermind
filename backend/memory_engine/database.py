import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import memory_config

logger = logging.getLogger("memory_engine.database")

db_url = memory_config.DATABASE_URL

# Adjust sqlite URL or postgres prefix if needed
connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,   # Liveness check on checkout prevents "SSL connection closed unexpectedly"
    "pool_recycle": 300,     # Recycle idle pool connections every 5 minutes
}

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

if "postgresql" in db_url:
    # Set TCP keepalives to prevent cloud middleboxes / firewalls from dropping idle SSL connections
    connect_args.update({
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    })
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_engine(db_url, connect_args=connect_args, **engine_kwargs)
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
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        db.close()
