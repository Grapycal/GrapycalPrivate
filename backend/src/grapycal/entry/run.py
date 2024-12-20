import asyncio
import os
import random
import sys
import threading
from contextlib import asynccontextmanager
import traceback
from typing import Awaitable, Callable

from grapycal.core.background_runner import RunnerInterrupt
import uvicorn
from grapycal.entry.args import parse_args
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from grapycal import OpenAnotherWorkspaceStrategy

from grapycal.core.workspace import Workspace
from topicsync.server.client_manager import (
    ClientCommProtocol,
    ConnectionClosedException,
)


class MyOpenAnotherWorkspaceStrategy(OpenAnotherWorkspaceStrategy):
    def __init__(self):
        super().__init__()
        self.path = None

    def open(self, path: str):
        self.path = path


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


class ThreadingEventWithReturn:
    def __init__(self):
        self._event = threading.Event()
        self._value = None

    def set(self, value):
        self._value = value
        self._event.set()

    def wait(self):
        self._event.wait()
        return self._value


def make_app(
    workspace: Workspace,
    frontend_path: str | None,
    event_loop_event: ThreadingEventWithReturn,
):
    if os.getenv("BEHIND_PROXY"):
        ROOT_PATH = os.getenv("ROOT_PATH", "/minilab")
        ROOT_PATH_IN_SERVERS = os.getenv("ROOT_PATH_IN_SERVERS", False)
        settings = {
            "root_path": ROOT_PATH,
            "root_path_in_servers": ROOT_PATH_IN_SERVERS,
        }
    else:
        settings = {}

    @asynccontextmanager
    async def lifespan(fastapi):
        event_loop_event.set(asyncio.get_event_loop())
        yield

    app = FastAPI(lifespan=lifespan, **settings)

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        client = Client(websocket.receive_text, websocket.send_text)
        try:
            await workspace._objectsync._topicsync.handle_client(client)
        except SystemExit:
            workspace.exit()

    @app.get("/download/{path:path}")
    async def download(path: str):
        '''Download local file by path'''
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="File not found: " + path)
        return FileResponse(path)

    if frontend_path is not None:

        @app.get("/", response_class=HTMLResponse)
        async def read_root():
            return open(frontend_path + "/index.html").read()

        app.mount("/", StaticFiles(directory=frontend_path), name="static")

    return app


def run_uvicorn(app, host, port):
    uvicorn.run(app, host=host, port=port, log_level="error")
    print("uvicorn exited")
    sys.exit(1)


def main():
    args = parse_args()

    # because args.frontend_path and args.extensions_path are NOT relative to the cwd,
    # we need to make them absolute before moving to the cwd
    if args.frontend_path is not None:
        args.frontend_path = os.path.abspath(args.frontend_path)

    if args.extensions_path is not None:
        args.extensions_path = os.path.abspath(args.extensions_path)

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
            f"Port {args.port} is already in use. Maybe another instance of grapycal is running? Consider changing the port with the --port argument."
        )
        print("Exiting")
        sys.exit(1)

    sys.path.append(args.cwd)

    # make extensions available
    if args.extensions_path is not None:
        sys.path.append(args.extensions_path)

    open_another = MyOpenAnotherWorkspaceStrategy()

    workspace = Workspace(args.file, open_another)

    event_loop_event = ThreadingEventWithReturn()
    app = make_app(workspace, args.frontend_path, event_loop_event)

    threading.Thread(
        target=run_uvicorn, args=(app, args.host, args.port), daemon=True
    ).start()

    ui_event_loop = event_loop_event.wait()

    try:
        workspace.run(ui_event_loop)
    except KeyboardInterrupt:
        print("Exiting")
        sys.exit(1)
    except RunnerInterrupt:
        print("Exiting")
        sys.exit(1)
    except Exception:
        # if we get here, usually because fail to load the workspace. So have to open another workspace to avoid infinite failure
        print("Something went wrong:")
        print(traceback.format_exc())
        here = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(here, "_grapycal_open_another_workspace.txt"), "w") as f:
            f.write(f"workspace_{random.randint(100000, 999999)}.grapycal")

    if open_another.path is not None:
        print(f"User wants to open another workspace: {open_another.path}.")
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "_grapycal_open_another_workspace.txt"), "w") as f:
            f.write(open_another.path)


if __name__ == "__main__":
    main()
