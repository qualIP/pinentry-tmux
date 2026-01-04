import sys
from pathlib import Path
from typing import TypeVar, override

from textual import work
from textual.app import App, ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Footer, Header

ReturnType = TypeVar("ReturnType")


class DialogApp(App[ReturnType]):
    CSS_PATH = "pinentry_tmux.ui.tcss"

    dialog: ModalScreen[ReturnType]

    def __init__(self, dialog: ModalScreen[ReturnType],
                 prog: str | None = None) -> None:
        super().__init__()
        self.title = prog or Path(sys.argv[0]).stem.replace('_', '-')
        self.dialog = dialog

    @override
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()

    @work
    async def on_mount(self) -> None:
        result = await self.push_screen_wait(self.dialog)
        self.exit(result=result)


def run_dialog[ReturnType](dialog: ModalScreen[ReturnType]) -> ReturnType | None:
    return DialogApp(dialog).run()
