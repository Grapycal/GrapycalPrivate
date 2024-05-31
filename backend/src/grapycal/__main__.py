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

    RESOURCE_SERVER = "https://resource.grapycal.com"

    # login first
    try:
        session = requests.Session()
        session.post(
            f"{RESOURCE_SERVER}/token",
            data={"password": "demo:@J%^INTERACTIVITYcounts2hqw45"},
        )
    except Exception:
        print("Failed to check for updates. No internet connection.")
        return

    def build_info():
        current_version = ""
        platform = ""
        with open(GRAPYCAL_ROOT / "build_info.json") as build_info_file:
            build_info = json.load(build_info_file)
            current_version = build_info["version"]
            platform = build_info["platform"]

        return current_version, platform

    def version_url_to_version(url):
        return url.split("/")[-1]

    def check_update():
        latest_url = f"{RESOURCE_SERVER}/latest/releases/demo"
        latest_version_url = session.get(latest_url).text.strip('" ')
        latest_version = version_url_to_version(latest_version_url)

        current_version, platform = build_info()

        # there will be a grapycal prefix in latest version
        if f"grapycal-{current_version}" == latest_version:
            return None

        print(
            f"Current version: grapycal-{current_version}, latest version: {latest_version}"
        )

        return f"{latest_version_url}-{platform}"

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
        # notice that after the installer, PATH of grapycal is changed
        _, platform = build_info()
        if "windows" in platform:
            # in windows,
            os.execl(
                sys.executable,
                sys.executable,
                extract_path / "install.py",
                "--message",
                f'"Grapycal updated to {version_url_to_version(extract_path.name)}. Please start Grapycal with `grapycal run` command"',
            )
        else:
            os.execl(
                sys.executable, sys.executable, extract_path / "install.py", "--launch"
            )

    if download_url := check_update():
        need_update = ask_update()

        if need_update:
            print(f"Downloading {download_url}...")
            update_url = f"{RESOURCE_SERVER}/{download_url}.zip"
            pack_zip = download(update_url)

            new_grapycal_name = version_url_to_version(download_url)
            grapycal_parent = GRAPYCAL_ROOT.parent
            extract_path = grapycal_parent / new_grapycal_name
            print(f"Extracting to {extract_path}...")
            pack_zip.extractall(extract_path)

            # copy the license file
            if (GRAPYCAL_ROOT / "license.json").exists():
                Path(extract_path / "license.json").write_text(
                    (GRAPYCAL_ROOT / "license.json").read_text()
                )
            print("Installing...")
            install(extract_path)
            install(
                extract_path,
            )


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
    with open(GRAPYCAL_ROOT / "build_info.json") as build_info_file:
        build_info = json.load(build_info_file)
        version = build_info["version"]
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
