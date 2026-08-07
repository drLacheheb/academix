import os
import sys

from core.infrastructure.db.pipeline_repository import PipelineJobRepository
from core.infrastructure.logging.logger import get_logger

logger = get_logger("migration-runner")


def main():
    logger.info("Initializing Standalone Migration Runner...")
    db_url = os.environ.get("DATABASE_URL", "sqlite:///academix.db")

    try:
        # 1. Run Alembic migrations if alembic.ini exists
        if os.path.exists("alembic.ini"):
            from alembic import command
            from alembic.config import Config

            logger.info("Running Alembic schema migrations (alembic upgrade head)...")
            alembic_cfg = Config("alembic.ini")
            alembic_cfg.set_main_option("sqlalchemy.url", db_url)
            command.upgrade(alembic_cfg, "head")
            logger.success("Alembic schema migrations completed successfully!")
        else:
            logger.info("No alembic.ini found, skipping Alembic CLI step.")

        # 2. Initialize database tables via SQLAlchemy metadata
        logger.info(f"Initializing database tables via PipelineJobRepository (DB: {db_url})...")
        repo = PipelineJobRepository(db_url)
        repo.init_db()
        logger.success("Database tables initialized successfully!")

    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
