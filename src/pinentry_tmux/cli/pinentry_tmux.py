#!/usr/bin/env python3
"""pinentry-tmux main entry point.

This implementation parses a subset of the Assuan protocol commands required for GPG pinentry interaction:
* SETDESC – set description (ignored in this stub)
* SETPROMPT – set prompt text
* GETPIN – request passphrase; the program will prompt the user via the terminal and return the value to GPG.
* BYE – terminate the session.

The real implementation would launch a tmux window and use the ``textual`` library for a richer UI.  For the purposes of unit and contract tests, a simple stdin/stdout interaction suffices.
"""

import argparse
import contextlib
import dataclasses
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import typing
import urllib.parse
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, TextIO

from pinentry_tmux.lib.assuan import AssuanErrors, AssuanSession
from pinentry_tmux.model.pinentry import PinentryState
from pinentry_tmux.ui.dialog import run_dialog
from pinentry_tmux.ui.pinentry_dialog import PinentryDialog

log = logging.getLogger("pinentry-tmux")


class Args:
    debug: bool

    tty: Path | None
    display: str | None
    timeout: float | None

    control_dir: Path | None
    intercept_log: Path | None


args: Args


class redirect_stdin(contextlib._RedirectStream):  # noqa: N801 # pyright: ignore[reportMissingTypeArgument,reportPrivateUsage]
    """Analogous to contextlib.redirect_stdout and contextlib.redirect_stderr"""

    _stream: str = "stdin"


class PinentryAssuanSession(AssuanSession):
    state: PinentryState

    def __init__(self, **kwargs: Any) -> None:
        self.state = PinentryState()
        super().__init__(**kwargs)

    def handle_bye(self, command: str, params: str | None) -> None:
        self.send("OK", "closing connection")
        self.exit(0)

    def handle_setdesc(self, command: str, params: str | None) -> None:
        self.state.description = urllib.parse.unquote(params or "") or None
        self.send("OK")

    def handle_setkeyinfo(self, command: str, params: str | None) -> None:
        self.state.keyinfo = (params or "").strip()
        self.send("OK")

    def handle_setprompt(self, command: str, params: str | None) -> None:
        self.state.prompt = urllib.parse.unquote(params or "")
        self.send("OK")

    def handle_seterror(self, command: str, params: str | None) -> None:
        self.state.error_msg = (params or "").strip()
        self.send("OK")

    def handle_getinfo(self, command: str, params: str | None) -> None:
        match params:
            case "flavor":
                self.send("D", "qip:tmux")
                self.send("OK")
            case "version":
                from pinentry_tmux import __version__

                self.send("D", str(__version__))
                self.send("OK")
            case "ttyinfo":
                # See `cmd_getinfo()` in https://github.com/gpg/pinentry/blob/master/pinentry/pinentry.c
                try:
                    ttyname = self.state.get_string_option("ttyname", "") or os.ttyname(0)
                except Exception:
                    ttyname = None
                ttystat = os.stat(ttyname) if ttyname else None
                ttytype = self.state.get_string_option("ttytype", "") or os.environ.get("TERM", None)
                self.send(
                    "D",
                    " ".join(
                        [
                            ttyname or "-",
                            ttytype or "-",
                            os.environ.get("DISPLAY", "-"),
                            f"{ttystat.st_mode}/{ttystat.st_uid}/{ttystat.st_gid}" if ttystat else "-",
                            f"{os.geteuid()}/{os.getegid()}",
                            "-",
                        ]
                    ),
                )
                self.send("OK")
            case "pid":
                self.send("D", f"{os.getpid()}")
                self.send("OK")
            case _:
                pass

    def handle_option(self, command: str, params: str | None) -> None:
        if not params:
            raise ValueError("Invalid OPTION command parameters")
        if "=" in params:
            option, value = params.split("=", 1)
        else:
            option, value = params, True
        option = option.strip()
        self.state.options[option] = value

        match option:
            case "owner" if value is not True:
                if m := re.match(r"^(?P<owner_pid>\d+)(?:/(?P<owner_uid>\d+))?(?: (?P<owner_host>\S+))?$", value):
                    self.state.owner_pid = int(m.group("owner_pid"))
                    if m.group("owner_uid"):
                        self.state.owner_uid = int(m.group("owner_uid"))
                    if m.group("owner_host"):
                        self.state.owner_host = m.group("owner_host")
            case _:
                pass

        self.send("OK")

    def handle_getpin(self, command: str, params: str | None) -> None:
        """Handle GETPIN by launching a tmux window that runs the UI.

        The UI process communicates via two named pipes: one for input (state) and
        another for output (response). This avoids any temporary regular files on
        disk.
        """

        log.debug("state: %r", self.state)
        if not os.environ.get("TMUX", None) and self.state.owner_pid is not None:
            try:
                environ_bytes = open(f"/proc/{self.state.owner_pid}/environ", "rb").read()
                environ = dict(item.split(b"=", 1) for item in environ_bytes.split(b"\x00") if b"=" in item)
                if b"TMUX" in environ:
                    os.environ["TMUX"] = environ[b"TMUX"].decode("ascii")
            except Exception as e:
                log.debug("Failed to get environment of PID %d: %s", self.state.owner_pid, e)

        if os.environ.get("TMUX", None) and (tmux := shutil.which("tmux")):
            # To support cases where a TTY pinentry would not play nice with
            # the current foreground application (e.g., Neovim), open a UI in a
            # "remote" TMUX window.

            # Create a secure temporary directory
            with tempfile.TemporaryDirectory(prefix="pinentry_tmux_") as tmp_dir:
                tmp_dir = Path(tmp_dir)
                # Ensure only the owner can access the temp dir
                tmp_dir.chmod(0o700)
                # Create FIFOs with mode 0600 (owner read/write only)
                in_fifo = tmp_dir / "in.fifo"
                os.mkfifo(in_fifo, mode=0o600)
                out_fifo = tmp_dir / "out.fifo"
                os.mkfifo(out_fifo, mode=0o600)

                # pinentry-tmux command
                cmd = [
                    sys.executable,
                    "-m",
                    "pinentry_tmux.cli.pinentry_tmux",
                    "--remote",
                    str(tmp_dir),
                ]
                if log.isEnabledFor(logging.DEBUG):
                    cmd += ["--debug"]

                # tmux command
                cmd = [
                    tmux,
                    "new-window",
                    "-n",
                    "pinentry",
                    subprocess.list2cmdline(cmd),
                ]

                log.debug("Running %r", cmd)
                subprocess.run(cmd, check=True)

                # Transfer state through the input FIFO.
                with in_fifo.open("w") as in_f:
                    state_dict = dataclasses.asdict(self.state)
                    log.debug("Sending state: %r", state_dict)
                    json.dump(state_dict, in_f)
                    in_f.write("\n\n")  # Add line end and an empty line to signify end of "packet"

                # Read the response from the output FIFO.
                with out_fifo.open("r") as out_f:
                    response = PinentryResponse(**_read_json_until_success(out_f))

        else:
            # Run on this TTY

            ttyname = self.state.get_string_option("ttyname", "")
            if not ttyname:
                raise ValueError("No TTY name given")
            with redirect_stdout(open(ttyname, "w")), redirect_stdin(open(ttyname, "r")):
                response = run_getpin_ui(self.state)

        if response.error_code:
            self.err(response.error_code, response.error_message)
        else:
            if response.passphrase:
                self.send("D", f"{response.passphrase}")
            self.send("OK")


@dataclasses.dataclass
class PinentryResponse:
    error_code: AssuanErrors = AssuanErrors.GPG_ERR_NO_ERROR
    error_message: str = ""  # If error_code
    passphrase: str = ""  # If !error_code


def _read_json_until_success(fp: TextIO) -> Any:
    """Read from `fp` until a complete JSON object can be parsed."""
    buf = ""
    while True:
        chunk = fp.readline()
        if not chunk:
            raise EOFError
        buf += chunk
        if not chunk.isspace():
            # "Packets" end with an empty line
            continue
        try:
            return json.loads(buf)
        except json.JSONDecodeError as exc:
            msg = str(exc).lower()
            if "expecting value" in msg or "unterminated string" in msg:
                continue  # keep reading
            raise


def run_getpin_ui(state: PinentryState) -> PinentryResponse:
    log.debug("run_dialog")
    ret = run_dialog(PinentryDialog(state))
    if ret is None:
        ret = AssuanErrors.GPG_ERR_CANCELED, "operation aborted"
    log.debug("return: ret=%r", ret)
    error_code, error_message = ret

    if error_code == AssuanErrors.GPG_ERR_NO_ERROR:
        log.debug("return: OK")
        response = PinentryResponse(passphrase=error_message)
    else:
        log.debug("return: %r %r", error_code, error_message)
        response = PinentryResponse(error_code=error_code, error_message=error_message)

    return response


def remote_getpin(control_dir: Path) -> None:
    """Run a Textual UI that prompts for the passphrase.

    The function reads state via JSON from `in_fifo` displays the dialog,
    writes the entered value to `out_fifo`, then exits.
    """

    in_fifo = control_dir / "in.fifo"
    out_fifo = control_dir / "out.fifo"

    cmd = [
        "tmux",
        "set-option",
        "-w",
        "remain-on-exit",
        "failed",
    ]
    log.debug("Running %r", cmd)
    subprocess.run(cmd)  # check=False

    with in_fifo.open("r") as f:
        state = PinentryState(**_read_json_until_success(f))

    response = run_getpin_ui(state)

    with out_fifo.open("w") as f:
        response_dict = dataclasses.asdict(response)
        log.debug("Sending response: %r", response_dict)
        json.dump(response_dict, f)
        f.write("\n\n")  # Add line end and an empty line to signify end of "packet"


def main() -> None:
    global args
    logging.basicConfig()

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--debug", "-d", default=False, action="store_true", help="Turn on debugging output")
    parser.add_argument("--display", "-D", default=None, help="Set the X display")
    parser.add_argument(
        "--timeout",
        "-o",
        default=None,
        type=float,
        help="Timeout waiting for input after this many seconds",
    )

    # TODO:
    # parser.add_argument("--ttyname", "-T", default=None,
    #                     help="Set the tty terminal node name")
    # parser.add_argument("--ttytype", "-N", default=None,
    #                     help="Set the tty terminal type")
    # parser.add_argument("--lc-ctype", "-C", default=None,
    #                     help="Set the tty LC_CTYPE value")
    # parser.add_argument("--lc-messages", "-M", default=None,
    #                     help="Set the tty LC_MESSAGES value")
    # parser.add_argument("--no-global-grab", "-g", default=None,
    #                     help="Grab keyboard only while window is focused")
    # parser.add_argument("--parent-wid", "-W", default=None,
    #                     help="Parent window ID (for positioning)")
    # parser.add_argument("--colors", "-c", default=None,
    #                     help="Set custom colors for ncurses")
    # parser.add_argument("--ttyalert", "-a", default=None,
    #                     help="Set the alert mode (none, beep or flash)")

    parser.add_argument(
        "--remote",
        dest="control_dir",
        default=None,
        type=Path,
        help="Run in remote UI mode with a control directory",
    )
    parser.add_argument("--tty", "-T", default=None, type=Path, help="Run in original TTY request mode")
    parser.add_argument("--intercept-log", default=None, type=Path, help="Intercept log path")

    args = typing.cast(Args, typing.cast(object, parser.parse_args()))

    if args.debug:
        log.setLevel(logging.DEBUG)

    if args.control_dir:
        # Running as a remote UT, presumably inside a tmux window
        remote_getpin(args.control_dir)

    elif args.display and (pinentry_x11 := shutil.which("pinentry-x11")):
        # X11 mode

        os.execv(pinentry_x11, sys.argv[1:])
        raise AssertionError("unreachable")  # pyright: ignore[reportUnreachable]

    else:
        assuan = PinentryAssuanSession(
            in_file=sys.stdin,
            out_file=sys.stdout,
            intercept_log=args.intercept_log,
        )

        sys.stdin = open("/dev/null")
        sys.stdout = open("/dev/null")
        if args.tty:
            assuan.state.options["ttyname"] = os.fspath(args.tty)

        if args.timeout is not None:
            assuan.state.timeout = args.timeout
        assuan.greet()
        assuan.communicate()
        sys.exit(assuan.exit_code)


if __name__ == "__main__":
    main()
