"""
Database migrations for schema updates.
Runs after init_db. For clean install, create_all handles everything.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def run_migrations(engine: AsyncEngine) -> None:
    """Run migrations for existing databases."""
    async with engine.connect() as conn:
        # Add birth_month, birth_approximate, death_month, death_approximate to graves
        for col, col_type, default in [
            ("birth_month", "INTEGER", "NULL"),
            ("birth_approximate", "INTEGER", "0"),
            ("death_month", "INTEGER", "NULL"),
            ("death_approximate", "INTEGER", "0"),
        ]:
            try:
                await conn.execute(
                    text(f"ALTER TABLE graves ADD COLUMN {col} {col_type} DEFAULT {default}")
                )
                await conn.commit()
                logger.info("Migration: added graves.%s", col)
            except Exception as e:
                err = str(e).lower()
                if "duplicate" in err or "already exists" in err or "sqlite" in err and "graves" in err:
                    pass
                else:
                    logger.debug("Migration graves.%s: %s", col, e)
