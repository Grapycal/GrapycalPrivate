import argparse
from typing import Any

import usersettings


def parse_args(sync=True):
    parser = argparse.ArgumentParser(description="Grapycal backend server")
    parser.add_argument(
        "file", type=str, help="path to workspace file, relative to --cwd", nargs="?"
    )
    parser.add_argument(
        "--frontend-path", type=str, help="path to frontend code", required=False
    )
    parser.add_argument("--extensions-path", type=str, help="path to extensions folder")
    parser.add_argument("--cwd", type=str, help="working directory")
    parser.add_argument("--port", type=int, help="port to listen on")
    parser.add_argument("--host", type=str, help="host to listen on")
    parser.add_argument(
        "--profile",
        "-p",
        action="store_true",
        help="profile the server with viztracer. The output will be in prof.html",
    )
    args = parser.parse_args()

    if isinstance(args.file, str):
        if not args.file.endswith(".grapycal"):
            args.file += ".grapycal"

    if sync:
        sync_args_with_usersettings(args, {"port": 7943, "host": "localhost"})

    return args


def sync_args_with_usersettings(args: argparse.Namespace, defaults: dict[str, Any]):
    s = usersettings.Settings("Grapycal")
    s.load_settings()

    for name, default in defaults.items():
        if getattr(args, name) is not None:
            s[name] = getattr(args, name)
        else:
            setattr(args, name, s.get(name, default))

    if (
        "cwd" in s
        and args.cwd == s["cwd"]
        and "file" in s
        and s["file"] is not None
        and args.file is None
    ):
        args.file = s["file"]
    elif args.file is None:
        args.file = "workspace.grapycal"

    s["cwd"] = args.cwd
    s["file"] = args.file

    s.save_settings()
    return args
