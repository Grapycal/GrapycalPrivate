from contextlib import asynccontextmanager
import threading
from typing import Awaitable, Callable
from fastapi.staticfiles import StaticFiles
from grapycal.core import workspace
from args import parse_args
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import uvicorn
import sys
from topicsync.server.client_manager import ClientCommProtocol, ConnectionClosedException


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


def make_app(workspace, frontend_path:str|None):
    import os
    if os.getenv("BEHIND_PROXY"):
        ROOT_PATH = os.getenv("ROOT_PATH", "/minilab")
        ROOT_PATH_IN_SERVERS = os.getenv("ROOT_PATH_IN_SERVERS", False)
        settings = {
            "root_path": ROOT_PATH,
            "root_path_in_servers": ROOT_PATH_IN_SERVERS,
        }
    else:
        settings = {}
    app = FastAPI(
        **settings
    )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        client = Client(websocket.receive_text, websocket.send_text)
        await workspace._objectsync._topicsync.handle_client(client)

    if frontend_path is not None:

        @app.get("/", response_class=HTMLResponse)
        async def read_root():
            return open(frontend_path + "/index.html").read()

        app.mount("/", StaticFiles(directory=frontend_path), name="static")


    return app


def run_uvicorn(app, host, port):
    uvicorn.run(app, host=host, port=port)
    print("uvicorn exited")
    sys.exit(1)

def main():
    args = parse_args()
    print(args)

    # make sure port is not in use
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((args.host, args.port))
    if result == 0:
        print(f"Port {args.port} is already in use. Maybe another instance of grapycal is running?")
        print("Exiting")
        sys.exit(1)

    sys.path.append(args.backend_path)
    from grapycal.core.workspace import Workspace

    workspace = Workspace(args.path, "")

    app = make_app(workspace, args.get("frontend_path", None))
    thread = threading.Thread(target=run_uvicorn, args=(app, args.host, args.port),daemon=True)
    thread.start()

    try:
        workspace.run()
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(1)

if __name__ == "__main__":
    main()
