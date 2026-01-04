import copy
import re
from pathlib import Path
from typing import override

from textual import on
from textual.app import ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label

from pinentry_tmux.lib.assuan import AssuanErrors
from pinentry_tmux.model.pinentry import PinentryState


class PinentryDialogBase(ModalScreen[tuple[AssuanErrors, str]]):
    CSS_PATH = Path(__file__).parent / "pinentry_tmux.ui.tcss"
    BINDINGS = [
        # ('enter', 'ok', "Ok"),  # Using on_input_submitted instead
        ("escape", "cancel", "Cancel"),
    ]

    state: PinentryState

    def __init__(self, state: PinentryState) -> None:
        super().__init__()
        self.state = state

    def on_mount(self) -> None:
        if self.state.timeout is not None:
            self.set_timer(self.state.timeout, self.action_timeout)

    def action_timeout(self) -> None:
        self.dismiss((AssuanErrors.GPG_ERR_TIMEOUT, "Timeout"))

    @override
    def compose(self) -> ComposeResult:
        def prep_label(label: str | None) -> str | None:
            label = label and label.lstrip("\r\n")
            label = label and label.rstrip()
            return label or None

        label = prep_label(self.state.description)
        if label:
            yield Label(label, id="description")

        label = prep_label(self.state.prompt)
        if label:
            yield Label(label, id="prompt")

        yield Input(id="answer", password=True)

        if self.state.error_msg:
            yield Label(self.state.error_msg, id="error_msg")
        ok_label = self.state.get_string_option("default-ok", "OK")
        cancel_label = self.state.get_string_option("default-cancel", "Cancel")
        with Horizontal(id="buttons"):
            yield Button(ok_label, variant="success", id="ok")
            yield Button(cancel_label, variant="error", id="cancel")

    def on_input_submitted(self) -> None:
        return self.action_ok()

    @on(Button.Pressed, "#ok")
    def action_ok(self) -> None:
        self.dismiss((AssuanErrors.GPG_ERR_NO_ERROR, self.query_one("#answer", Input).value))

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.dismiss((AssuanErrors.GPG_ERR_CANCELED, "operation cancelled"))


def PinentryDialog(state: PinentryState) -> PinentryDialogBase:  # noqa: N802
    """Creates a PinentryDialog instance.
    This wrapper is necessary because textual doesn't support dynamic BINDINGS
    allocation, so a custom class must be created with custom a BINDINGS class
    variable.
    """

    BINDINGS: list[BindingType] = []  # noqa: N806
    state = copy.copy(state)
    state.options = copy.copy(state.options)

    ok_label = state.get_string_option("default-ok", "OK")
    ok_label.replace("[", r"\[")
    if m := re.match(r"_([A-Za-z])", ok_label):
        letter = m.group(1)
        ok_label = f"{ok_label[: m.span(0)[0]]}[underline]{letter}[/underline]{ok_label[m.span(0)[1] :]}"
        BINDINGS.append((f"ctrl+{letter.lower()}", "ok", ok_label))
    state.options["default-ok"] = ok_label

    cancel_label = state.get_string_option("default-cancel", "Cancel")
    cancel_label.replace("[", r"\[")
    if m := re.match(r"_([A-Za-z])", cancel_label):
        letter = m.group(1)
        cancel_label = f"{cancel_label[: m.span(0)[0]]}[underline]{letter}[/underline]{cancel_label[m.span(0)[1] :]}"
        BINDINGS.append((f"ctrl+{letter.lower()}", "cancel", cancel_label))
    state.options["default-cancel"] = cancel_label

    cls = type(
        "PinentryDialog",
        (PinentryDialogBase,),
        {
            "BINDINGS": BINDINGS,
        },
    )

    self = cls(state)

    return self
