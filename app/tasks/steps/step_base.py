import copy
from typing import Any


def update_required_arguments(interface_arguments: dict[str, Any],
                              task_attributes:dict[str, Any],
                              default_args:dict[str, Any]) -> dict[str, Any]:
    # apply values from task attributes to the interface arguments into a new dictionary
    all_args = copy.copy(interface_arguments)

    for key in interface_arguments.keys():
        if key in task_attributes:
            all_args[key] = task_attributes[key]

        if key in default_args:
            all_args[key] = default_args[key]

    return all_args
