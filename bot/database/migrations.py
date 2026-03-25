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

        # Add order assignment and photo tracking columns to orders
        order_columns = [
            ("grave_id", "INTEGER", "NULL"),
            ("assigned_telegram_id", "BIGINT", "NULL"),
            ("assigned_username", "VARCHAR(100)", "NULL"),
            ("assigned_at", "TIMESTAMP", "NULL"),
            ("reminder_sent", "BOOLEAN", "FALSE"),
            ("photo1_file_id", "VARCHAR(255)", "NULL"),
            ("photo2_file_id", "VARCHAR(255)", "NULL"),
            ("photos_uploaded_at", "TIMESTAMP", "NULL"),
        ]
        for col, col_type, default in order_columns:
            try:
                await conn.execute(
                    text(f"ALTER TABLE orders ADD COLUMN {col} {col_type} DEFAULT {default}")
                )
                await conn.commit()
                logger.info("Migration: added orders.%s", col)
            except Exception as e:
                err = str(e).lower()
                if "duplicate" in err or "already exists" in err:
                    pass
                else:
                    logger.debug("Migration orders.%s: %s", col, e)

        # Add delivery_fee, is_plantable, planting_fee to flower_products
        flower_columns = [
            ("delivery_fee", "INTEGER", "0"),
            ("is_plantable", "BOOLEAN", "FALSE"),
            ("planting_fee", "INTEGER", "0"),
        ]
        for col, col_type, default in flower_columns:
            try:
                await conn.execute(
                    text(f"ALTER TABLE flower_products ADD COLUMN {col} {col_type} DEFAULT {default}")
                )
                await conn.commit()
                logger.info("Migration: added flower_products.%s", col)
            except Exception as e:
                err = str(e).lower()
                if "duplicate" in err or "already exists" in err:
                    pass
                else:
                    logger.debug("Migration flower_products.%s: %s", col, e)

        # Add retry and feedback columns to orders
        retry_columns = [
            ("retry_deadline", "TIMESTAMP", "NULL"),
            ("retry_reminder_sent", "BOOLEAN", "FALSE"),
            ("feedback", "VARCHAR(20)", "NULL"),
        ]
        for col, col_type, default in retry_columns:
            try:
                await conn.execute(
                    text(f"ALTER TABLE orders ADD COLUMN {col} {col_type} DEFAULT {default}")
                )
                await conn.commit()
                logger.info("Migration: added orders.%s", col)
            except Exception as e:
                err = str(e).lower()
                if "duplicate" in err or "already exists" in err:
                    pass
                else:
                    logger.debug("Migration orders.%s: %s", col, e)

        # Add feedback_reason column to orders
        try:
            await conn.execute(
                text("ALTER TABLE orders ADD COLUMN IF NOT EXISTS feedback_reason TEXT")
            )
            await conn.commit()
            logger.info("Migration: added orders.feedback_reason")
        except Exception as e:
            err = str(e).lower()
            if "duplicate" in err or "already exists" in err:
                pass
            else:
                logger.debug("Migration orders.feedback_reason: %s", e)
