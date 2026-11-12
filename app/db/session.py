from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
import traceback
from sqlmodel import SQLModel, Session as SQLModelSession

from . import logger
from app.config import get_config


class Database:
    def __init__(
        self,
        db_url: str = None,
        pool_size: int = None,
        max_overflow: int = None,
        pool_timeout: int = None,
        pool_recycle: int = None,
    ) -> None:
        config = get_config()
        self._engine = create_engine(
            db_url or config.get_database_url,
            echo=False,
            pool_size=pool_size
            if pool_size is not None
            else config.DB_POOL_SIZE,
            max_overflow=max_overflow
            if max_overflow is not None
            else config.DB_MAX_OVERFLOW,
            pool_timeout=pool_timeout
            if pool_timeout is not None
            else config.DB_POOL_TIMEOUT,
            pool_recycle=pool_recycle
            if pool_recycle is not None
            else config.DB_POOL_RECYCLE,
            pool_pre_ping=True,
            connect_args={
                "options": "-c statement_timeout=30000"  # 30 second query timeout
            },
        )

        # Add connection pool monitoring
        self._setup_connection_monitoring()

    def _setup_connection_monitoring(self):
        """Add event listeners for connection pool monitoring"""

        @event.listens_for(self._engine, "connect")
        def set_connection_info(dbapi_connection, connection_record):
            logger.debug("New database connection created")

        @event.listens_for(self._engine, "checkout")
        def receive_checkout(
            dbapi_connection, connection_record, connection_proxy
        ):
            pool = self._engine.pool
            logger.debug(
                f"Connection checked out. Pool status: size={pool.size()}, "
                f"checked_out={pool.checkedout()}, overflow={pool.overflow()}, "
                f"checked_in={pool.checkedin()}"
            )

            # Warn when approaching pool limits
            total_connections = pool.size() + pool.overflow()
            if total_connections > 1 and pool.checkedout() > (
                total_connections * 0.8
            ):
                logger.warning(
                    f"Connection pool usage high: {pool.checkedout()}/{total_connections} connections in use"
                )

        @event.listens_for(self._engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            logger.debug("Connection returned to pool")

    def create_database(self) -> None:
        try:
            SQLModel.metadata.create_all(self._engine)
        except Exception as e:
            logger.error(f"Exception in create_database: {str(e)}")
            logger.error(traceback.format_exc())
            return
        logger.info("Tables setup complete")

    @contextmanager
    def session(self) -> Generator[SQLModelSession, None, None]:
        session: SQLModelSession = SQLModelSession(self._engine)
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            session.rollback()
            raise
        finally:
            session.close()
            logger.debug("Database session closed")

    def get_pool_status(self) -> dict:
        """Get current connection pool status for monitoring"""
        pool = self._engine.pool
        return {
            "pool_size": pool.size(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "checked_in": pool.checkedin(),
            "total_capacity": pool.size() + pool.overflow(),
        }
