#!/bin/bash
cwd=$(pwd)
parent_path=$( cd "$(dirname "${BASH_SOURCE[0]}")" ; pwd -P )

cd "$parent_path/.."

python scripts/build_frontend.py &&\
python entry/standalone/launcher.py --backend-path "backend/src" --frontend-path "frontend/dist" --extensions-path "extensions" --port 7943 --cwd $cwd $1
