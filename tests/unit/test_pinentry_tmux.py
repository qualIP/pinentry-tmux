"""
Tests that the output of ``pinentry-tmux`` does not change.
"""

import io
import os
from collections.abc import Callable
from pathlib import Path

import pytest

import pinentry_tmux
from pinentry_tmux.cli.pinentry_tmux import PinentryAssuanSession

test_dir = Path(__file__).parent


def run_session(
    input_data: str,
    session_setup: Callable[[PinentryAssuanSession], None] | None = None,
) -> str:
    in_stream = io.StringIO(input_data)
    out_stream = io.StringIO()
    session = PinentryAssuanSession(
        in_file=in_stream,
        out_file=out_stream,
    )
    if session_setup:
        session_setup(session)
    # Greet first (as the real program would)
    session.greet()
    # Process commands
    session.communicate()
    return out_stream.getvalue()


class TestPinentryTmux:
    @classmethod
    def setup_class(cls):
        _ = os.environ.pop("DISPLAY", None)
        _ = os.environ.pop("GPG_TTY", None)
        _ = os.environ.pop("TMUX", None)
        _ = os.environ.pop("TTY", None)

    def do_io_test(
        self,
        input_file: str | Path,
        golden_file: str | Path,
        session_setup: Callable[[PinentryAssuanSession], None] | None = None,
    ) -> None:
        pty_master, pty_slave = os.openpty()
        ttyname = os.ttyname(pty_slave)

        input_file = test_dir / input_file
        golden_file = test_dir / golden_file
        input_data = input_file.read_text(encoding="utf-8")
        input_data = input_data.format(
            ttyname=ttyname,
        )

        output = run_session(input_data, session_setup=session_setup)

        if False and not golden_file.exists():
            # First run – generate the golden file for future comparisons
            golden_file.write_text(output, encoding="utf-8")  # pyright: ignore[reportUnreachable]
            pytest.skip("Golden file created – rerun test to verify consistency.")

        expected = golden_file.read_text(encoding="utf-8")
        expected = expected.replace("\n", "\r\n")
        expected = expected.format(
            ttyname=ttyname,
            pid=os.getpid(),
            version=pinentry_tmux.__version__,
            ttystat=os.stat(ttyname),
            euid=os.geteuid(),
            egid=os.getegid(),
        )

        os.close(pty_master)
        os.close(pty_slave)

        assert output == expected

    def test_basic(self):
        self.do_io_test(
            "test_pinentry_tmux_input1.txt",
            "test_pinentry_tmux_output1.txt",
        )

    def test_timeout(self):
        def session_setup(session: PinentryAssuanSession) -> None:
            session.state.timeout = 0.1

        self.do_io_test(
            "test_pinentry_tmux_input_timeout.txt",
            "test_pinentry_tmux_output_timeout.txt",
            session_setup=session_setup,
        )
