import logging
from contextlib import AbstractContextManager
from typing import Callable

from sqlmodel import Session

from app.model.dto.model_public import ModelPublic
from app.repository.interface_repository import InterfaceRepository

logger = logging.getLogger()

class ModelService:
    def __init__(
        self,
        session_factory: Callable[..., AbstractContextManager[Session]],
        interface_repository: InterfaceRepository,
    ):
        self .session_factory = session_factory
        self.interface_repository = interface_repository

    def get_segmentation_interfaces(self) -> list[ModelPublic]:
        with self.session_factory() as session:
            self.interface_repository.set_session(session)
            segmentation_interfaces = self.interface_repository.get_by_group_name("Classification")

            result_list = []
            for interface in segmentation_interfaces:
                logger.info(f"Segmentation interface: {interface.name}")
                model = ModelPublic(id=interface.id, name=interface.name,
                                    description=interface.description)
                result_list.append(model)

            return result_list