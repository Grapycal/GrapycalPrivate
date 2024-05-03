import os
import webbrowser

here = os.path.dirname(os.path.abspath(__file__))
os.chdir(here)

webbrowser.open("http://localhost:7943/frontend")

os.system(
    'python entry/launcher.py --backend-path "backend/src" --frontend-path "frontend" --port 7943 --cwd "files"'
)
