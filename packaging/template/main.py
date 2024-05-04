import os
import threading
import time
import webbrowser

import grapycal
import termcolor

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)


def open_browser():
    time.sleep(4)
    webbrowser.open("http://localhost:7943/frontend")


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
    + termcolor.colored("http://localhost:7943/frontend", "green")
    + " with Chrome to access the frontend.\n"
)

print("=" * 50)

os.system(
    'python entry/launcher.py --backend-path "backend/src" --frontend-path "frontend" --port 7943 --cwd "files"'
)
