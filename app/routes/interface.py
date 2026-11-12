import logging
from typing import List

from dependency_injector.wiring import Provide, inject
from fastapi import Depends, APIRouter

from app.container import Container
from app.model.dto.model_public import ModelPublic
from app.service.model_service import ModelService

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/segmentation", response_model=List[ModelPublic])
@inject
def get_segmentation_models(
        model_service: ModelService = Depends(Provide[Container.model_service]),
) -> list[ModelPublic]:
    logging.info("get all project")
    all_models = model_service.get_segmentation_interfaces()
    return all_models
