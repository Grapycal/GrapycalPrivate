import os
import subprocess
import time
import webbrowser

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)

subprocess.Popen('python entry/launcher.py --backend-path "backend/src" --frontend-path "frontend" --port 7943', shell=True)

time.sleep(2)

webbrowser.open('http://localhost:7943/frontend')