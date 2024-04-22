import argparse
from typing import Any
import usersettings


def parse_args():
    parser = argparse.ArgumentParser(description="Grapycal backend server")
    parser.add_argument(
        "file", type=str, help="path to workspace file, relative to --cwd", nargs="?"
    )
    parser.add_argument(
        "--backend-path", type=str, help="path to backend code", required=True
    )
    parser.add_argument(
        "--frontend-path", type=str, help="path to frontend code", required=True
    )
    parser.add_argument("--extensions-path", type=str, help="path to extensions folder")
    parser.add_argument("--cwd", type=str, help="working directory")
    parser.add_argument("--port", type=int, help="port to listen on")
    parser.add_argument("--host", type=str, help="host to listen on")
    args = parser.parse_args()

    sync_args_with_usersettings(
        args, {"file": "workspace.grapycal", "port": 7943, "host": "localhost"}
    )

    return args


def sync_args_with_usersettings(args: argparse.Namespace, defaults: dict[str, Any]):
    s = usersettings.Settings("Grapycal")
    s.load_settings()

    for name, default in defaults.items():
        if getattr(args, name) is not None:
            s[name] = getattr(args, name)
        else:
            setattr(args, name, s.get(name, default))
    s.save_settings()
    return args
