#!/bin/bash

python scripts/build_frontend.py &&\
python -m grapycal.entry.launcher --backend-path "backend/src" --frontend-path "frontend/dist" --extensions-path "extensions" --port 7943 --cwd "dev_cwd" $1
