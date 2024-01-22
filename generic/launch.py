#!/usr/bin/env python3

from pathlib import Path
import tempfile
from argparse import ArgumentParser, Namespace
import time
import subprocess
import sys


class DockerContainer:
    def __init__(self, container_id: str) -> None:
        self._container_id = container_id

    def __enter__(self) -> None:
        pass

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback
    ) -> None:
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
        "--width",
        default=1280,
        type=int,
        metavar="WIDTH",
    )
    parser.add_argument(
        "--height",
        default=720,
        type=int,
        metavar="HEIGHT",
    )
    parser.add_argument(
        "--depth",
        default=24,
        type=int,
        choices=(8, 16, 24),
        metavar="DEPTH",
    )
    parser.add_argument(
        "--vnc-port",
        default=9090,
        type=int,
        metavar="VNC_PORT",
    )
    parser.add_argument(
        "--vnc-password-file",
        type=Path,
        required=True,
        metavar="PASSWORD_FILE"
    )

    options = parser.parse_args()

    if options.width < 1280 or 3840 < options.width:
        msg = (
            f"{options.width}: `--width` must be an integer "
            "within the range [1280, 3840]."
        )
        raise RuntimeError(msg)

    if options.height < 720 or 2160 < options.height:
        msg = (
            f"{options.height}: `--height` must be an integer "
            "within the range [720, 2160]."
        )
        raise RuntimeError(msg)

    if options.vnc_port <= 1024 or 49152 <= options.vnc_port:
        msg = f"{options.vnc_port}: An invalid value for `--vnc-port`."
        raise RuntimeError(msg)

    if not options.vnc_password_file.exists():
        msg = f"{options.vnc_password_file}: Does not exist."
        raise RuntimeError(msg)
    if not options.vnc_password_file.is_file():
        msg = "f{options.vnc_password_file}: Not a file."
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
            "cryolite/majsoulvnc",
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
            "-v",
            "/run/dbus:/host/run/debus",
            "-p",
            f"{options.vnc_port}:9090",
            "-itd",
            "--rm",
            "cryolite/majsoulvnc",
            "sleep",
            "INFINITY",
        ),
        stdin=subprocess.DEVNULL,
        stdout=docker_run_stdout,
        text=True,
    )
    time.sleep(1.0)
    docker_run_stdout.seek(0)

    return docker_run_stdout.readline().rstrip('\n')


def _main() -> None:
    options = _parse_arguments()

    container_id = _run_container(options)

    with DockerContainer(container_id):
        result = subprocess.run(
            options.vnc_password_file.absolute(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=True,
            text=True,
        )
        print(result.stderr, file=sys.stdout, end='')
        print(result.stderr, file=sys.stderr, end='')
        vnc_password = result.stdout.splitlines()[0]

        if vnc_password.find("'") != -1:
            msg = "`--vnc-password` cannot contain any single quote `'`."
            raise RuntimeError(msg)

        subprocess.run(
            args=(
                "docker",
                "exec",
                container_id,
                "/bin/bash",
                "-c",
                f"echo '{vnc_password}' | vncpasswd -f > /home/ubuntu/.vnc/passwd",
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
                "chmod",
                "600",
                "/home/ubuntu/.vnc/passwd",
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
                "Xvnc",
                "-geometry",
                f"{options.width}x{options.height}",
                "-depth",
                str(options.depth),
                "-rfbport",
                "5900",
                "-rfbauth",
                "/home/ubuntu/.vnc/passwd",
                "-localhost",
                "+extension",
                "GLX",
                ":0",
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
                "--listen",
                "9090",
                "--vnc",
                "localhost:5900",
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
                container_id,
                "google-chrome",
                "--use-gl=egl",
                "--no-first-run",
                "--no-default-browser-check",
                f"--window-wize={options.width},{options.height}",
                "https://game.mahjongsoul.com/",
            ),
            stdin=subprocess.DEVNULL,
            check=True,
            text=True,
        )


if __name__ == "__main__":
    _main()
