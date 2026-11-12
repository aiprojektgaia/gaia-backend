from typing import List
from fastapi import APIRouter, Depends, HTTPException
from dependency_injector.wiring import inject, Provide

from app.container import Container
from app.model.dto.interface_public import InterfacePublic
from app.service.interface_service import InterfaceService
from app.usecase.verify_system_status import VerifySystemStatusUseCase
from app.model.system_status import SystemStatus

from app.db.session import Database

router = APIRouter(prefix="/status", tags=["status"])


@router.get("/verify", response_model=SystemStatus)
@inject
def verify_system_status(
    verify_system_status: VerifySystemStatusUseCase = Depends(
        Provide[Container.verify_system_status_usecase]
    ),
) -> SystemStatus:
    return verify_system_status.verify()


@router.get("/interfaces", response_model=List[InterfacePublic])
@inject
def get_interfaces(
    interface_service: InterfaceService = Depends(
        Provide[Container.interface_service]
    ),
) -> List[InterfacePublic]:
    interfaces = interface_service.get_installed_interfaces()
    if not interfaces:
        raise HTTPException(
            status_code=404, detail="No installed interfaces found"
        )
    return [InterfacePublic.from_interface_db(i) for i in interfaces]


@router.get("/ping")
def ping() -> str:
    return "Pong"


@router.get("/db-pool-status")
@inject
def get_database_pool_status(
    database: Database = Depends(Provide[Container.db]),
):
    """Get current database connection pool status for monitoring"""
    try:
        status = database.get_pool_status()

        # Add health assessment
        total_capacity = status["total_capacity"]
        used_connections = status["checked_out"]
        usage_percentage = (
            (used_connections / total_capacity) * 100
            if total_capacity > 0
            else 0
        )

        health_status = "healthy"
        if usage_percentage > 90:
            health_status = "critical"
        elif usage_percentage > 70:
            health_status = "warning"

        return {
            "pool_status": status,
            "usage_percentage": round(usage_percentage, 2),
            "health_status": health_status,
            "recommendations": get_pool_recommendations(status),
        }
    except Exception as e:
        return {"error": f"Failed to get pool status: {str(e)}"}


def get_pool_recommendations(status: dict) -> list[str]:
    """Provide recommendations based on pool status"""
    recommendations = []

    total_capacity = status["total_capacity"]
    used_connections = status["checked_out"]
    usage_percentage = (
        (used_connections / total_capacity) * 100 if total_capacity > 0 else 0
    )

    if usage_percentage > 90:
        recommendations.append(
            "Critical: Connection pool nearly exhausted - increase pool_size or max_overflow"
        )
    elif usage_percentage > 70:
        recommendations.append(
            "Warning: High connection pool usage - monitor for potential issues"
        )

    if status["overflow"] > 0:
        recommendations.append(
            "Using overflow connections - consider increasing base pool_size"
        )

    if not recommendations:
        recommendations.append("Connection pool is healthy")

    return recommendations
