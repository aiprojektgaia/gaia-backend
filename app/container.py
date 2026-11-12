from dependency_injector import containers, providers

from app.config import get_config
from app.db.session import Database
from app.repository.interface_repository import InterfaceRepository
from app.repository.project_repository import ProjectRepository
from app.repository.run_repository import ProjectRunRepository
from app.repository.run_type_repository import RunTypeRepository
from app.repository.task_repository import TaskRepository
from app.repository.task_step_repository import TaskStepRepository
from app.service.interface_service import InterfaceService
from app.service.model_service import ModelService
from app.service.project_service import ProjectService
from app.service.project_run_service import ProjectRunService
from app.service.dispatcher import Dispatcher
from app.tasks.process_handler import ProcessHandler
from app.usecase.create_project_run import CreateProjectRunUseCase
from app.usecase.delete_project_run import DeleteProjectRunUseCase
from app.usecase.get_project_run_status import GetProjectRunStatusUseCase
from app.usecase.download_run_result import DownloadRunResultUseCase
from app.usecase.handle_run_result import HandleRunResultUseCase
from app.usecase.mark_project_run_as_error import MarkProjectRunAsError
from app.usecase.verify_system_status import VerifySystemStatusUseCase


class Container(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        modules=[
            "app.routes.project",
            "app.routes.project_run",
            "app.routes.run_result",
            "app.routes.status",
            "app.routes.interface",
            "app.tasks.poller",
        ]
    )

    # Use config for database URL (pool settings now handled in Database class)
    config = providers.Singleton(get_config)

    # Pass pool settings from config to Database
    db = providers.Singleton(
        Database,
        db_url=config.provided.get_database_url,
        pool_size=config.provided.DB_POOL_SIZE,
        max_overflow=config.provided.DB_MAX_OVERFLOW,
        pool_timeout=config.provided.DB_POOL_TIMEOUT,
        pool_recycle=config.provided.DB_POOL_RECYCLE,
    )

    session_factory = db.provided.session

    project_repository = providers.Factory(ProjectRepository)

    interface_repository = providers.Factory(InterfaceRepository)
    project_run_repository = providers.Factory(ProjectRunRepository)
    run_type_repository = providers.Factory(RunTypeRepository)
    task_repository = providers.Factory(TaskRepository)
    task_step_repository = providers.Factory(TaskStepRepository)

    process_handler = providers.Singleton(
        ProcessHandler,
        session_factory=session_factory,
        task_step_repository=task_step_repository,
    )

    project_service = providers.Factory(
        ProjectService,
        session_factory=session_factory,
        project_repository=project_repository,
    )

    project_run_service = providers.Factory(
        ProjectRunService,
        session_factory=session_factory,
        project_run_repository=project_run_repository,
        task_repository=task_repository,
        process_handler=process_handler,
    )

    interface_service = providers.Factory(
        InterfaceService,
        session_factory=session_factory,
        interface_repository=interface_repository,
    )

    model_service = providers.Factory(
        ModelService,
        session_factory=session_factory,
        interface_repository=interface_repository,
    )

    create_project_run_usecase = providers.Factory(
        CreateProjectRunUseCase,
        session_factory=session_factory,
        project_repository=project_repository,
        project_run_repository=project_run_repository,
        run_type_repository=run_type_repository,
        task_repository=task_repository,
    )

    delete_project_run_usecase = providers.Factory(
        DeleteProjectRunUseCase,
        session_factory=session_factory,
        project_repository=project_repository,
        project_run_repository=project_run_repository,
        run_type_repository=run_type_repository,
        task_repository=task_repository,
        task_step_repository=task_step_repository,
    )

    handle_run_result_usecase = providers.Factory(
        HandleRunResultUseCase,
        session_factory=db.provided.session,
        task_repository=task_repository,
        task_step_repository=task_step_repository,
    )

    download_run_result_usecase = providers.Factory(
        DownloadRunResultUseCase,
        session_factory=session_factory,
        project_run_repository=project_run_repository,
        task_repository=task_repository,
        task_step_repository=task_step_repository,
    )

    mark_project_run_as_error_usecase = providers.Factory(
        MarkProjectRunAsError,
        session_factory=db.provided.session,
        task_repository=task_repository,
    )

    dispatcher = providers.Factory(
        Dispatcher,
        session_factory=session_factory,
        task_repository=task_repository,
        task_step_repository=task_step_repository,
        mark_project_run_as_error_usecase=mark_project_run_as_error_usecase,
    )

    get_project_run_status_usecase = providers.Factory(
        GetProjectRunStatusUseCase,
        session_factory=session_factory,
        project_run_repository=project_run_repository,
        task_repository=task_repository,
    )

    verify_system_status_usecase = providers.Factory(
        VerifySystemStatusUseCase,
        session_factory=session_factory,
        interface_repository=interface_repository,
    )
