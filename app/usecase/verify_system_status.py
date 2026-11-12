import logging
from sqlalchemy import text
from alembic import script
from alembic.runtime import migration
from alembic.config import Config
from sqlalchemy import engine

from app.system_state import system_state
from app.config import get_config
from app.helpers.path_helper import validate_path_access
from app.model.system_status import SystemComponentStatus, SystemStatus

from contextlib import AbstractContextManager
from typing import Callable

from sqlmodel import Session

from app.repository.interface_repository import InterfaceRepository


logger = logging.getLogger(__name__)


class VerifySystemStatusUseCase:
    """
    This use case is used to determine the status of the system and should be used
    when troubleshooting issues with it during runtime. It will typically be better
    to check logs and database yourself if you can, but this is an alternative.
    """

    @staticmethod
    def _safe(error: Exception) -> str:
        # Raw exception text can contain paths, hostnames and SQL; keep it in the log.
        logger.warning("System status check failed: %s", error)
        return "Check failed, see the backend log for details"

    @staticmethod
    def _path_message(ok: bool, detail: str, label: str) -> str:
        if ok:
            return f"{label} path is readable and writable"
        logger.warning("%s path check failed: %s", label, detail)
        return f"{label} path check failed, see the backend log for details"

    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        interface_repository: InterfaceRepository,
    ):
        self.session_factory = session_factory
        self.interface_repository = interface_repository

    def verify(self) -> SystemStatus:
        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            return self._verify()

    def _verify(self) -> SystemStatus:
        return SystemStatus(
            database=self._verify_database(),
            engine_filesystem=self._verify_engine_filesystem(),
            storage_filesystem=self._verify_storage_filesystem(),
            active_interfaces=self._verify_active_interfaces(),
            installing_interfaces=self._verify_installing_interfaces(),
            poller=self._verify_poller(),
            migrations=self._verify_migrations(),
        )

    def _verify_migrations(self) -> SystemComponentStatus:
        """
        https://alembic.sqlalchemy.org/en/latest/cookbook.html#test-current-database-revision-is-at-head-s
        """
        try:
            system_config = get_config()
            db_engine = engine.create_engine(system_config.get_database_url)

            with db_engine.connect() as connection:
                context = migration.MigrationContext.configure(connection)
                # TODO: Avoid pointing it to the alembic.ini file because of strange path issues.
                # Only the "script_location" key should be needed.
                alembic_cfg = Config()
                alembic_cfg.set_main_option("script_location", "app/alembic")
                directory = script.ScriptDirectory.from_config(alembic_cfg)

                # Compare the head from the database revision with the directories.
                up_to_date = set(context.get_current_heads()) == set(
                    directory.get_heads()
                )
                if not up_to_date:
                    return SystemComponentStatus(
                        ok=False,
                        message="Database Migrations are not up to date",
                    )

        except Exception as e:
            return SystemComponentStatus(ok=False, message=self._safe(e))

        return SystemComponentStatus(
            ok=True, message="Database Migrations are up to date"
        )

    def _verify_database(self) -> SystemComponentStatus:
        sql = text("SELECT 1")
        with self.session_factory() as session:
            try:
                session.exec(sql)
            except Exception as e:
                return SystemComponentStatus(ok=False, message=self._safe(e))

            return SystemComponentStatus(
                ok=True, message="Backend can connect to database"
            )

    def _verify_engine_filesystem(self) -> SystemComponentStatus:
        try:
            config = get_config()
            ok, message = validate_path_access(config.MODEL_BASE_PATH)
            return SystemComponentStatus(ok=ok, message=self._path_message(ok, message, "Engine"))
        except Exception as e:
            return SystemComponentStatus(ok=False, message=self._safe(e))

    def _verify_storage_filesystem(self) -> SystemComponentStatus:
        try:
            config = get_config()
            ok, message = validate_path_access(config.STORAGE_PATH)
            return SystemComponentStatus(ok=ok, message=self._path_message(ok, message, "Storage"))
        except Exception as e:
            return SystemComponentStatus(ok=False, message=self._safe(e))

    def _verify_active_interfaces(self) -> SystemComponentStatus:
        try:
            interfaces = self.interface_repository.get_all_eager()
            inactive_interfaces_paths = [
                i.name for i in interfaces if not i.is_active
            ]
            active_interfaces_paths = [
                i.name for i in interfaces if i.is_active
            ]
            return SystemComponentStatus(
                ok=len(inactive_interfaces_paths) == 0,
                message=f"The following interfaces are not active: ({', '.join(inactive_interfaces_paths)}), active interfaces are: ({', '.join(active_interfaces_paths)})",
            )

        except Exception as e:
            return SystemComponentStatus(ok=False, message=self._safe(e))

        return SystemComponentStatus(
            ok=True, message="All interfaces are active"
        )

    def _verify_installing_interfaces(self) -> SystemComponentStatus:
        if system_state.are_interfaces_installed():
            return SystemComponentStatus(
                ok=True,
                message="Interfaces have finished installing",
            )

        return SystemComponentStatus(
            ok=False,
            message="Interfaces are still being installed",
        )

    def _verify_poller(self) -> SystemComponentStatus:
        if system_state.is_poller_running():
            return SystemComponentStatus(
                ok=True,
                message="Poller is running as expected",
            )

        return SystemComponentStatus(
            ok=False,
            message="Poller is not running",
        )
