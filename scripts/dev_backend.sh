#!/bin/bash

python entry/standalone/launcher.py --backend-path "backend/src" --extensions-path "extensions" --port 7943 --cwd "dev_cwd" $1
