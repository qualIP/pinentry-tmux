"""Assuan protocol helper classes.

This module contains the core types used for handling the Assuan protocol.
"""

import enum
import logging
import os
import sys
import typing
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

log = logging.getLogger("assuan")


class AssuanErrors(enum.IntEnum):
    """Integer error codes used by GPG in the Assuan protocol.
    See gpg-error.h from libgpg-error-dev
    """

    GPG_ERR_NO_ERROR = 0
    GPG_ERR_GENERAL = 1
    GPG_ERR_TIMEOUT = 62
    GPG_ERR_INV_DATA = 79
    GPG_ERR_CANCELED = 99
    GPG_ERR_UNSUPPORTED_OPERATION = 124


class AssuanError(Exception):
    """Exception that carries an `AssuanErrors` error code."""

    def __init__(self, error: AssuanErrors, message: str) -> None:
        self.assuan_error = error
        super().__init__(message)


type AssuanCommandHandler = Callable[[str, str | None], None]


class AssuanSession:
    """Base class for reading/writing Assuan commands.

    Sub‑classes must implement handlers named ``handle_<command>``.  The base
    implementation reads lines from :attr:`in_file`, dispatches to the handler,
    and writes responses via :meth:`send`.
    """

    in_file: TextIO
    out_file: TextIO
    intercept_log: Path | None

    exit_code: int | None = None
    cur_command: str | None = None

    def __init__(
        self,
        *,
        in_file: TextIO,
        out_file: TextIO,
        intercept_log: Path | None = None,
    ) -> None:
        self.in_file = in_file
        self.out_file = out_file
        self.intercept_log = intercept_log

    def communicate(self) -> None:
        for raw_line in self.in_file:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            parts = line.split(maxsplit=1)
            match parts:
                case [command, params]:
                    pass
                case [command]:
                    params = None
                case _:
                    raise ValueError(f"Invalid Assuan line: {line!r}")
            self.log_traffic("<E", command, params)
            try:
                self.cur_command = command
                try:
                    handler = self.get_command_handler(command)
                except Exception as e:
                    self.exc(e)
                else:
                    try:
                        handler(command, params)
                    except Exception as e:
                        self.exc(e)
            finally:
                del self.cur_command
            if self.exit_code is not None:
                break

    def get_command_handler(self, command: str) -> AssuanCommandHandler:
        command = command.lower()
        try:
            return typing.cast(AssuanCommandHandler, getattr(self, f"handle_{command}"))
        except AttributeError:
            raise AssuanError(AssuanErrors.GPG_ERR_UNSUPPORTED_OPERATION, f"unknown command {command!r}") from None

    def exit(self, exit_code: int) -> None:
        self.exit_code = exit_code

    def send(self, code: str, params: str | None = None) -> None:
        """Send a message followed by CRLF as required by Assuan."""
        if params:
            self.out_file.write(f"{code} {params}\r\n")
        else:
            # params is None or ''
            self.out_file.write(f"{code}\r\n")
        try:
            self.out_file.flush()
        except BrokenPipeError:
            log.debug("flush: broken pipe")
            sys.exit(0)
        self.log_traffic(">U", code, params)

    def exc(self, exc: Exception) -> None:
        match exc:
            case AssuanError():
                self.err(exc.assuan_error, str(exc))
            case ValueError():
                self.err(AssuanErrors.GPG_ERR_INV_DATA, str(exc))
            case _:
                self.err(AssuanErrors.GPG_ERR_GENERAL, str(exc))

    def err(self, error: AssuanErrors, message: str) -> None:
        self.send("ERR", f"{int(error)} {message}")

    def greet(self) -> None:
        self.send("OK", f"Pleased to meet you, process {os.getpid()}")

    def log_traffic(self, direction: str, code: str, params: str | None) -> None:
        if self.cur_command == "GETPIN" and code == "D":
            params = "***REDACTED***"
        log_format = "Assuan[%s] %r %r"
        log.debug(log_format, direction, code, params)
        if self.intercept_log:
            with self.intercept_log.open("a") as f:
                f.write(log_format % (direction, code, params))
                f.write("\n")
                f.flush()
