class SystemState:
    """
    Used for troubleshooting purposes to validate if the installation has finished
    and if the poller is running as expected.
    """

    is_installing_interfaces: bool
    poller_task_running: bool

    def __init__(self):
        self.is_installing_interfaces = False
        self.poller_task_running = False

    def set_interfaces_installed(self):
        self.is_installing_interfaces = False

    def set_poller_running(self):
        self.poller_task_running = True

    def are_interfaces_installed(self):
        return not self.is_installing_interfaces

    def is_poller_running(self):
        return self.poller_task_running


# To ensure we don't use multiple instances of the same object, this is the only thing
# that should be imported by other files
system_state = SystemState()
