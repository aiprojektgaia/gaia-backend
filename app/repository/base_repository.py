from sqlmodel import Session as SQLModelSession
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    def __init__(self):
        self.session: SQLModelSession | None = None

    def set_session(self, session: SQLModelSession) -> None:
        self.session = session

    def safe_rollback(self) -> None:
        """Safe rollback that doesn't raise exceptions"""
        try:
            if self.session:
                self.session.rollback()
        except Exception as e:
            logger.error(f"Error during rollback: {str(e)}")
