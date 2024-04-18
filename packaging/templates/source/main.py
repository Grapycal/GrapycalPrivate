import os
import webbrowser

webbrowser.open('http://localhost:7943/frontend')

os.system('python entry/launcher.py --backend-path "backend/src" --frontend-path "frontend" --port 7943')