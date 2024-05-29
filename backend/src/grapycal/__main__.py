import json
import os
import pathlib
import threading
import time
import webbrowser
import psutil
import zipfile
from io import BytesIO
from pathlib import Path
import shutil
import sys
import termcolor

CWD = os.getcwd()
HERE = pathlib.Path(__file__).parent
GRAPYCAL_ROOT = HERE.parent.parent.parent
os.environ["GRAPYCAL_ROOT"] = str(GRAPYCAL_ROOT)


def input_colored(prompt):
    return input(termcolor.colored(prompt, "green"))


def update_if_needed():
    import requests

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
            ans = input_colored(
                "Grapycal update available, download and install? (y/n) "
            )
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


def license_file_exists():
    return Path(GRAPYCAL_ROOT / "license.json").exists()


def acquire_license():
    import requests

    serial = input_colored("Please enter your serial number: ")

    def get_ip_addresses(family):
        for interface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == family:
                    yield snic.address

    macs = list(get_ip_addresses(psutil.AF_LINK))

    if len(macs) == 0:
        print("No MAC address found, please connect to a network to acquire license.")
        sys.exit(1)

    # do not accept too many mac addresses, otherwise the license would be abused
    macs = macs[:10]
    response = requests.post(
        "https://license.grapycal.com/license",
        json={"serial_number": serial, "mac_addresses": macs, "user_name": "demo"},
    )

    if response.status_code == 200:
        response = response.json()
        print(
            "License acquired successfully. Remaining uses: ",
            response["remaining_uses"],
        )
        with open(GRAPYCAL_ROOT / "license.json", "w") as f:
            json.dump(response["license"], f)
    elif response.status_code == 403:
        print(
            "Invalid serial number. Maybe it has been used too many times, or it's invalid."
        )
        sys.exit(1)
    else:  # error
        print(
            "Failed to acquire license, please try again.",
            response.status_code,
            response.text,
        )
        sys.exit(1)


def print_welcome():
    # not using grapycal.__version__ because it's slow
    # instead read from __init__.py, find the line __version__ = "..."
    with open(HERE / "__init__.py") as f:
        for line in f:
            if line.startswith("__version__"):
                version = line.split('"')[1].split('"')[0]
                break
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


def run():
    print("Checking for updates...")
    update_if_needed()

    if not license_file_exists():
        print("License not found. Acquiring license...")
        acquire_license()

    def open_browser():
        time.sleep(4)
        webbrowser.open("http://localhost:7943")

    threading.Thread(target=open_browser).start()

    while True:
        print_welcome()
        core_return_code = os.system(
            f'python {HERE/"entry/launcher.py"} --frontend-path {GRAPYCAL_ROOT/"frontend"} --port 7943 --cwd {CWD}'
        )

        if core_return_code in [3, 4, 5]:
            acquire_license()
        else:
            break


def dev():
    # python scripts/build_frontend.py
    os.system(f"python {GRAPYCAL_ROOT/'scripts/build_frontend.py'}")
    try:
        os.system(
            f'python {HERE/"entry/launcher.py"} --frontend-path {GRAPYCAL_ROOT/"frontend/dist"} --port 7943 --cwd {CWD}'
        )
    except KeyboardInterrupt:
        pass


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "run"
    if command == "run":
        run()
    elif command == "dev":
        dev()
    else:
        print("Avaliable commands: run, dev")
