import dataclasses
from typing import Literal, TypedDict


class PinentryOptions(TypedDict, total=False):
    method: Literal["window", "popup"]
    ttyname: str

@dataclasses.dataclass
class PinentryState:
    description: str | None = None
    keyinfo: str | None = None
    prompt: str = "PIN:"
    error_msg: str = ""
    options: PinentryOptions = dataclasses.field(default_factory=dict)  # pyright: ignore[reportAssignmentType, reportUnknownVariableType]
    timeout: float | None = None

    owner_pid: int | None = None
    owner_uid: int | None = None
    owner_host: str | None = None

    def get_string_option(self, option: str, default: str) -> str:
        value = self.options.get(option, None)
        match value:
            case str():
                return value
            case _:
                return default
