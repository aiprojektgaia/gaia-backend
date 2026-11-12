from pydantic import BaseModel


class SystemComponentStatus(BaseModel):
    ok: bool
    message: str


class SystemStatus(BaseModel):
    database: SystemComponentStatus
    migrations: SystemComponentStatus
    engine_filesystem: SystemComponentStatus
    storage_filesystem: SystemComponentStatus
    active_interfaces: SystemComponentStatus
    installing_interfaces: SystemComponentStatus
    poller: SystemComponentStatus
