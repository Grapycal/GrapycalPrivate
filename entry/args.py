import argparse
import usersettings
import os


def parse_args():
    parser = argparse.ArgumentParser(description="Grapycal backend server")
    parser.add_argument(
        "path", type=str, help="path to workspace file", nargs="?", default=None
    )
    parser.add_argument("--backend-path", type=str, help="path to backend code")
    parser.add_argument("--frontend-path", type=str, help="path to frontend code")
    parser.add_argument("--port", type=int, help="port to listen on")
    parser.add_argument(
        "--http-port", type=int, help="http port to listen on (to serve webpage)"
    )
    parser.add_argument("--host", type=str, help="host to listen on")
    parser.add_argument(
        "--no-http",
        action="store_true",
        help="if set, the server does not serve the webpage",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="if set, the workspace restarts when it exits. Convenient for development",
    )
    args = parser.parse_args()
    s = usersettings.Settings("Grapycal")
    s.add_setting("port", int, default=8765)  # type: ignore
    s.add_setting("http_port", int, default=9001)  # type: ignore
    s.add_setting("host", str, default="localhost")  # type: ignore
    s.add_setting("path", str, default=os.path.join("workspace.grapycal"))  # type: ignore

    s.load_settings()
    for name in ["port", "host", "path", "http_port"]:
        if getattr(args, name):
            s[name] = getattr(args, name)
    s.save_settings()

    for name in ["backend_path", "frontend_path", "no_http", "restart"]:
        if getattr(args, name):
            s[name] = getattr(args, name)

    return s
