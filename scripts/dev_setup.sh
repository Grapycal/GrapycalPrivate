#!/bin/bash
git submodule update --init --recursive &&\

# setup backend (Python) environment
pip install -e submodules/topicsync &&\
pip install -e submodules/objectsync &&\
pip install -e backend &&\
pip install -e extensions/grapycal_builtin &&\

# setup frontend (JavaScript) environment
cd frontend && npm install && cd .. &&\
cd submodules/topicsync-client && npm install && cd ../.. &&\
cd submodules/objectsync-client && npm install && cd ../.. &&\

echo "Setup complete. Run 'scripts/dev.sh' to start the server."
