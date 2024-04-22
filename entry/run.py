import os
import sys
import threading
from typing import Awaitable, Callable

import uvicorn
from args import parse_args
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from topicsync.server.client_manager import (
    ClientCommProtocol,
    ConnectionClosedException,
)


class Client(ClientCommProtocol):
    def __init__(
        self,
        recieve_text: Callable[[], Awaitable[str]],
        send_text: Callable[[str], Awaitable[None]],
    ):
        self._recieve_text = recieve_text
        self._send_text = send_text

    async def messages(self):
        try:
            while True:
                yield await self._recieve_text()
        except Exception as e:
            raise ConnectionClosedException(e)

    async def send(self, message):
        try:
            await self._send_text(message)
        except Exception as e:
            raise ConnectionClosedException(e)


def make_app(workspace, frontend_path: str | None):
    app = FastAPI()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        client = Client(websocket.receive_text, websocket.send_text)
        await workspace._objectsync._topicsync.handle_client(client)

    if frontend_path is not None:

        @app.get("/frontend/", response_class=HTMLResponse)
        async def read_root():
            return open(frontend_path + "/index.html").read()

        app.mount("/frontend/", StaticFiles(directory=frontend_path), name="static")

    return app


def run_uvicorn(app, host, port):
    uvicorn.run(app, host=host, port=port)
    print("uvicorn exited")
    sys.exit(1)


def main():
    args = parse_args()
    print(args)

    # because args.backend_path and args.frontend_path are NOT relative to args.cwd,
    # we need to make them absolute
    args.backend_path = os.path.abspath(args.backend_path)
    if args.frontend_path is not None:
        args.frontend_path = os.path.abspath(args.frontend_path)

    # set cwd to args.cwd
    if args.cwd is not None:
        os.makedirs(args.cwd, exist_ok=True)
        os.chdir(args.cwd)

    # make sure port is not in use
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((args.host, args.port))
    if result == 0:
        print(
            f"Port {args.port} is already in use. Maybe another instance of grapycal is running?"
        )
        print("Exiting")
        sys.exit(1)

    # make extensions available
    if args.extensions_path is not None:
        sys.path.append(args.extensions_path)

    # before importing workspace, we need to add the backend path to sys.path
    sys.path.append(args.backend_path)
    from grapycal.core.workspace import Workspace

    workspace = Workspace(args.file, "")

    app = make_app(workspace, args.frontend_path)
    threading.Thread(
        target=run_uvicorn, args=(app, args.host, args.port), daemon=True
    ).start()

    try:
        workspace.run()
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(1)


if __name__ == "__main__":
    main()
