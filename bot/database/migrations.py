"""
Database migrations for schema updates.
Runs after init_db. For clean install, create_all handles everything.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncConnection

logger = logging.getLogger(__name__)


async def _create_financial_tables(conn: AsyncConnection) -> None:
    """Create financial tracking tables if they don't exist."""

    # Service Catalog
    try:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS service_catalog (
                id SERIAL PRIMARY KEY,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                base_price NUMERIC(12, 2) NOT NULL DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.commit()
        logger.info("Migration: created service_catalog table")
    except Exception as e:
        if "already exists" not in str(e).lower():
            logger.debug("Migration service_catalog: %s", e)

    # Cemetery Pricing
    try:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS cemetery_pricing (
                id SERIAL PRIMARY KEY,
                name VARCHAR(300) NOT NULL,
                district VARCHAR(200),
                region VARCHAR(200),
                price_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.00,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.commit()
        logger.info("Migration: created cemetery_pricing table")
    except Exception as e:
        if "already exists" not in str(e).lower():
            logger.debug("Migration cemetery_pricing: %s", e)

    # Service Pricing Rules
    try:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS service_pricing_rules (
                id SERIAL PRIMARY KEY,
                service_id INTEGER REFERENCES service_catalog(id) ON DELETE CASCADE,
                cemetery_id INTEGER REFERENCES cemetery_pricing(id) ON DELETE CASCADE,
                custom_price NUMERIC(12, 2),
                platform_percent NUMERIC(5, 2) NOT NULL DEFAULT 30.00,
                worker_percent NUMERIC(5, 2) NOT NULL DEFAULT 70.00,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.commit()
        logger.info("Migration: created service_pricing_rules table")
    except Exception as e:
        if "already exists" not in str(e).lower():
            logger.debug("Migration service_pricing_rules: %s", e)

    # Order Financials
    try:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS order_financials (
                id SERIAL PRIMARY KEY,
                order_id INTEGER UNIQUE,
                user_id INTEGER,
                user_telegram_id BIGINT,
                service_id INTEGER REFERENCES service_catalog(id) ON DELETE SET NULL,
                service_name VARCHAR(200) NOT NULL,
                cemetery_id INTEGER REFERENCES cemetery_pricing(id) ON DELETE SET NULL,
                cemetery_name VARCHAR(300) NOT NULL DEFAULT '—',
                worker_id INTEGER,
                worker_telegram_id BIGINT,
                worker_username VARCHAR(100),
                base_price NUMERIC(12, 2) NOT NULL DEFAULT 0,
                price_multiplier NUMERIC(4, 2) NOT NULL DEFAULT 1.00,
                final_price NUMERIC(12, 2) NOT NULL DEFAULT 0,
                platform_percent NUMERIC(5, 2) NOT NULL DEFAULT 30.00,
                worker_percent NUMERIC(5, 2) NOT NULL DEFAULT 70.00,
                platform_earning NUMERIC(12, 2) NOT NULL DEFAULT 0,
                worker_earning NUMERIC(12, 2) NOT NULL DEFAULT 0,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.commit()
        logger.info("Migration: created order_financials table")
    except Exception as e:
        if "already exists" not in str(e).lower():
            logger.debug("Migration order_financials: %s", e)

    # Worker Earnings
    try:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS worker_earnings (
                id SERIAL PRIMARY KEY,
                worker_telegram_id BIGINT UNIQUE NOT NULL,
                worker_username VARCHAR(100),
                total_orders INTEGER DEFAULT 0,
                completed_orders INTEGER DEFAULT 0,
                returned_orders INTEGER DEFAULT 0,
                canceled_orders INTEGER DEFAULT 0,
                total_earned NUMERIC(14, 2) DEFAULT 0,
                pending_earnings NUMERIC(14, 2) DEFAULT 0,
                last_order_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.commit()
        logger.info("Migration: created worker_earnings table")
    except Exception as e:
        if "already exists" not in str(e).lower():
            logger.debug("Migration worker_earnings: %s", e)

    # Daily Revenue
    try:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS daily_revenue (
                id SERIAL PRIMARY KEY,
                date TIMESTAMP UNIQUE NOT NULL,
                total_orders INTEGER DEFAULT 0,
                completed_orders INTEGER DEFAULT 0,
                returned_orders INTEGER DEFAULT 0,
                canceled_orders INTEGER DEFAULT 0,
                total_revenue NUMERIC(14, 2) DEFAULT 0,
                platform_revenue NUMERIC(14, 2) DEFAULT 0,
                worker_payouts NUMERIC(14, 2) DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.commit()
        logger.info("Migration: created daily_revenue table")
    except Exception as e:
        if "already exists" not in str(e).lower():
            logger.debug("Migration daily_revenue: %s", e)

    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_service_catalog_active ON service_catalog(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_cemetery_pricing_active ON cemetery_pricing(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_pricing_rule_service ON service_pricing_rules(service_id)",
        "CREATE INDEX IF NOT EXISTS idx_pricing_rule_cemetery ON service_pricing_rules(cemetery_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_fin_order_id ON order_financials(order_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_fin_status ON order_financials(status)",
        "CREATE INDEX IF NOT EXISTS idx_order_fin_worker ON order_financials(worker_telegram_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_fin_service ON order_financials(service_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_fin_cemetery ON order_financials(cemetery_id)",
        "CREATE INDEX IF NOT EXISTS idx_order_fin_created ON order_financials(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_worker_earnings_telegram ON worker_earnings(worker_telegram_id)",
        "CREATE INDEX IF NOT EXISTS idx_daily_revenue_date ON daily_revenue(date)",
    ]

    for idx_sql in indexes:
        try:
            await conn.execute(text(idx_sql))
            await conn.commit()
        except Exception:
            pass  # Index might already exist


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

        # Create financial tables
        await _create_financial_tables(conn)
