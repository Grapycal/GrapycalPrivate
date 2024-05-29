import json
import os
import pathlib
import threading
import time
import webbrowser
import psutil
import requests
import zipfile
from io import BytesIO
from pathlib import Path
import shutil
import sys
import termcolor

import grapycal

CWD = os.getcwd()
HERE = pathlib.Path(__file__).parent
GRAPYCAL_ROOT = HERE.parent.parent.parent


def input_colored(prompt):
    return input(termcolor.colored(prompt, "green"))


def update_if_needed():
    # login first
    session = requests.Session()
    session.post(
        "https://resource.grapycal.com/token",
        data={"password": "demo:@J%^INTERACTIVITYcounts2hqw45"},
    )

    def check_update():
        from importlib.metadata import version
        latest_url = 'https://resource.grapycal.com/latest/releases/demo'
        latest_version = session.get(latest_url)
        current_version = version('grapycal')
        if current_version in latest_version:
            return None

        # select os

        import platform
        os_name = ''
        platform_name = platform.system()
        if platform_name == 'Windows':
            os_name = 'windows.x86_64'
        elif platform_name == 'Linux':
            os_name = 'linux.x86_64'
        else:  # assume darwin
            if 'arm' in platform.machine():  # aarch
                os_name = 'darwin.aarch64'
            else:
                os_name = 'darwin.x86_64'

        return f"{latest_version}-{os_name}"

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

    def install(extract_path: Path):
        # chdir here is safe, because at the end of install the new grapycal will be started
        chdir(extract_path)
        installer_path = os.getcwd() /'backend'/'src'/'grapycal'/'standalone_utils'/'install.py'
        exec(open(installer_path).read())

        # replace new grapycal with the current one
        # notice that after the installer, PATH of grapycal is changed
        os.execlp('grapycal')

    if new_grapycal_name := check_update():
        update_url = f'https://resource.grapycal.com/releases/demo/{new_grapycal_name}.zip'
        need_update = ask_update()

        if need_update:
            pack_zip = download(update_url)
            grapycal_parent = GRAPYCAL_ROOT.parent
            extract_path = grapycal_parent / new_grapycal_name
            pack_zip.extractall(extract_path)
            install(extract_path)


def license_file_exists():
    return Path(GRAPYCAL_ROOT / "license.json").exists()


def acquire_license():
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


def run_core():
    return os.system(
        f'python {HERE/"entry/launcher.py"} --backend-path {GRAPYCAL_ROOT/"backend/src"} --frontend-path {GRAPYCAL_ROOT/"frontend"} --port 7943 --cwd {CWD}'
    )


def main():
    os.environ["GRAPYCAL_ROOT"] = str(GRAPYCAL_ROOT)

    print("Checking for updates...")

    # if updated, this function will not return back
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
        core_return_code = run_core()

        if core_return_code in [3, 4, 5]:
            acquire_license()
        else:
            break
