import os
import pathlib
import threading
import time
import webbrowser
import requests
import zipfile
from io import BytesIO
from pathlib import Path
import shutil
import sys
import termcolor


def main():
    CWD = os.getcwd()
    HERE = pathlib.Path(__file__).parent
    GRAPYCAL_ROOT = HERE.parent.parent.parent
    os.environ["GRAPYCAL_ROOT"] = str(GRAPYCAL_ROOT)

    # login first
    session = requests.Session()
    session.post(
        "https://resource.grapycal.com/token",
        data={"password": "demo:@J%^INTERACTIVITYcounts2hqw45"},
    )

    def check_update():
        return "https://resource.grapycal.com/releases/demo/grapycal-0.11.3-e52a16demo-darwin.aarch64.zip"

    def ask_update():
        while True:
            ans = input("Grapycal update available, download and install? y/n ")
            match ans:
                case "y" | "Y":
                    return True
                case "n" | "N":
                    return False
                case _:
                    print("Please input y or n")

    def download(url: str):
        response = session.get(url)
        return zipfile.ZipFile(
            BytesIO(response.content), compression=zipfile.ZIP_DEFLATED
        )

    def install(extract_path: str):
        # First remove everything (except this file)
        # Remove current file will cause a crash
        for filename in os.listdir(HERE):
            if filename != "main.py" and filename != extract_path:
                dest_path = Path(HERE) / filename
                if os.path.isfile(dest_path):
                    os.remove(dest_path)
                elif os.path.isdir(dest_path):
                    shutil.rmtree(dest_path)

        # Move everything from extract_path to the current folder (except this file)
        for filename in os.listdir(extract_path):
            if filename != "main.py":
                shutil.move(Path(extract_path) / filename, Path(HERE))

        # update instruction for updater
        with open("update", "w") as f:
            print(
                f"u {extract_path} main.py", file=f
            )  # update main.py, new file in extract_path
            print(f"rmtree {extract_path}", file=f)
            print("r install.py", file=f)

        # updater will replace current process
        # inherit environment, use same python
        # all arguments are passed to updater, so updater can start updated main.py again with the same arguments
        os.execv(sys.executable, ["python", "updater.py"] + sys.argv)

    if update_url := check_update():
        need_update = ask_update()

        if need_update:
            pack_zip = download(update_url)
            print("before extract")
            pack_zip.extractall("extracted")
            install("extracted")  # this is a non-returning function

    import grapycal  # noqa importimg grapycal requires the license check to pass

    os.chdir(HERE)

    def open_browser():
        time.sleep(4)
        webbrowser.open("http://localhost:7943")

    threading.Thread(target=open_browser).start()

    version = grapycal.__version__
    print(
        termcolor.colored(
            r"""
        ______                                  __
        / ____/________ _____  __  ___________ _/ /
        / / __/ ___/ __ `/ __ \/ / / / ___/ __ `/ /
        / /_/ / /  / /_/ / /_/ / /_/ / /__/ /_/ / /
        \____/_/   \__,_/ .___/\__, /\___/\__,_/_/
                    /_/    /____/
                                    """,
            "red",
        )
        + termcolor.colored("v" + version, "white")
    )

    print(
        "\nWelcome to Grapycal. Please go to "
        + termcolor.colored("http://localhost:7943", "green")
        + " with Chrome to access the frontend.\n"
    )

    print("=" * 50)

    os.system(
        f'python entry/launcher.py --backend-path {GRAPYCAL_ROOT/"backend/src"} --frontend-path {GRAPYCAL_ROOT/"frontend"} --port 7943 --cwd {CWD}'
    )
