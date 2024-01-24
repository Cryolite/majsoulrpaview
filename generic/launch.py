#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import time
from argparse import ArgumentParser, Namespace
from pathlib import Path


class DockerContainer:
    def __init__(self, container_id: str) -> None:
        self._container_id = container_id

    def __enter__(self) -> None:
        pass

    def __exit__(self, exc_type, exc_value, traceback) -> None:  # noqa: ANN001
        subprocess.run(
            args=(
                "docker",
                "container",
                "stop",
                self._container_id,
            ),
            stdin=subprocess.DEVNULL,
            check=True,
            text=True,
        )


def _parse_arguments() -> Namespace:
    parser = ArgumentParser()
    parser.add_argument(
        "--viewport-height",
        default=720,
        type=int,
        metavar="VIEWPORT_HEIGHT",
    )
    parser.add_argument(
        "--depth",
        default=24,
        type=int,
        choices=(8, 16, 24),
        metavar="DEPTH",
    )
    parser.add_argument(
        "--remote-host",
        default='127.0.0.1',
        metavar="REMOTE_HOST",
    )
    parser.add_argument(
        "--remote-port",
        default=19222,
        type=int,
        metavar="REMOTE_PORT",
    )
    parser.add_argument(
        "--message-queue-port",
        default=37247,
        type=int,
        metavar="MESSAGE_QUEUE_PORT",
    )
    parser.add_argument(
        "--novnc-port",
        default=6080,
        type=int,
        metavar="NOVNC_PORT",
    )
    parser.add_argument(
        "--vnc-password-file",
        type=Path,
        required=True,
        metavar="PASSWORD_FILE",
    )

    options = parser.parse_args()

    if options.viewport_height < 720 or 2160 < options.viewport_height:
        msg = (
            f"{options.viewport_height}: `--viewport-height` must be "
            "an integer within the range [720, 2160]."
        )
        raise RuntimeError(msg)

    if options.remote_port <= 1024 or 49152 <= options.remote_port:
        msg = f"{options.remote_port}: An invalid value for `--remote-port`."
        raise RuntimeError(msg)

    if options.message_queue_port <= 1024 or 49152 <= options.message_queue_port:
        msg = (
            f"{options.message_queue_port}:"
            " An invalid value for `--message-queue-port`."
        )
        raise RuntimeError(msg)

    if options.novnc_port < 1024 or 49151 < options.novnc_port:
        msg = f"{options.novnc_port}: An invalid value for `--novnc-port`."
        raise RuntimeError(msg)

    if not options.vnc_password_file.exists():
        msg = f"{options.vnc_password_file}: Does not exist."
        raise RuntimeError(msg)
    if not options.vnc_password_file.is_file():
        msg = f"{options.vnc_password_file}: Not a file."
        raise RuntimeError(msg)

    return options


def _run_container(options: Namespace) -> str:
    subprocess.run(
        args=(
            "docker",
            "build",
            "--pull",
            "--progress=plain",
            "-t",
            "cryolite/majsoulrpaview:generic",
            ".",
        ),
        stdin=subprocess.DEVNULL,
        check=True,
        text=True,
    )

    docker_run_stdout = tempfile.TemporaryFile("w+t", encoding="UTF-8")
    subprocess.Popen(
        args=(
            "docker",
            "run",
            "--cap-add",
            "SYS_ADMIN",
            "-p",
            f"{options.novnc_port}:6080",
            "-d",
            "--rm",
            "cryolite/majsoulrpaview:generic",
            "sleep",
            "INFINITY",
        ),
        stdin=subprocess.DEVNULL,
        stdout=docker_run_stdout,
        text=True,
    )
    time.sleep(1.0)
    docker_run_stdout.seek(0)

    return docker_run_stdout.readline().rstrip("\n")


def _main() -> None:
    options = _parse_arguments()

    width = (options.viewport_height // 9) * 16
    height = (width * 3) // 4

    container_id = _run_container(options)

    with DockerContainer(container_id):
        result = subprocess.run(
            options.vnc_password_file.absolute(),  # noqa: S603
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=True,
            text=True,
        )
        print(result.stderr, file=sys.stdout, end="")
        print(result.stderr, file=sys.stderr, end="")
        vnc_password = result.stdout.splitlines()[0]
        if vnc_password.find("'") != -1:
            msg = "`--vnc-password` cannot contain any single quote `'`."
            raise RuntimeError(msg)

        subprocess.run(
            args=(
                "docker",
                "exec",
                "-d",
                container_id,
                "Xvfb",
                ":0",
                "-screen",
                "0",
                f"{width}x{height}x{options.depth}",
                "+extension",
                "GLX",
            ),
            stdin=subprocess.DEVNULL,
            check=True,
            text=True,
        )

        subprocess.run(
            args=(
                "docker",
                "exec",
                container_id,
                "x11vnc",
                "-storepasswd",
                vnc_password,
                ".vnc/passwd",
            ),
            stdin=subprocess.DEVNULL,
            check=True,
            text=True,
        )

        subprocess.run(
            args=(
                "docker",
                "exec",
                "-d",
                container_id,
                "x11vnc",
                "-display",
                ":0",
                "-rfbport",
                "5900",
                "-geometry",
                f"{width}x{height}",
                "-shared",
                "-forever",
                "-loop",
                "-localhost",
                "-o",
                "x11vnc.log",
                "-repeat",
                "-rfbauth",
                ".vnc/passwd",
            ),
            stdin=subprocess.DEVNULL,
            check=True,
            text=True,
        )

        subprocess.run(
            args=(
                "docker",
                "exec",
                "-d",
                container_id,
                "/usr/share/novnc/utils/launch.sh",
            ),
            stdin=subprocess.DEVNULL,
            check=True,
            text=True,
        )

        subprocess.run(
            args=(
                "docker",
                "exec",
                "-e",
                "DISPLAY=:0",
                "-d",
                container_id,
                "bash",
                "-c",
                (
                    ". majsoulrpa/.venv/bin/activate; "
                    "majsoulrpa_remote_browser"
                    f" --remote_host {options.remote_host}"
                    f" --remote_port {options.remote_port}"
                    f" --message_queue_port {options.message_queue_port}"
                    f" --viewport_height {options.viewport_height}"
                ),
            ),
            stdin=subprocess.DEVNULL,
            check=True,
            text=True,
        )

        input("Press any key to kill the remote browser...")


if __name__ == "__main__":
    _main()
