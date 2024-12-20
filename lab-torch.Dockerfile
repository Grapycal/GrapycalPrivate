FROM python:3.11-bookworm AS backend-builder

WORKDIR /opt/grapycal

COPY .git .git
COPY .gitmodules .gitmodules

COPY submodules/topicsync submodules/topicsync
COPY submodules/objectsync submodules/objectsync

RUN git submodule update --init --recursive submodules/topicsync
RUN git submodule update --init --recursive submodules/objectsync

# Install Grapycal Lab Communication Core
RUN pip install -e submodules/topicsync
RUN pip install -e submodules/objectsync

# Install Grapycal Lab Core
COPY backend backend
RUN pip install -e backend

# Install Grapycal Lab Extensions
COPY extensions/grapycal_builtin extensions/grapycal_builtin
RUN pip install -e extensions/grapycal_builtin
COPY extensions/grapycal_torch extensions/grapycal_torch
RUN pip install -e extensions/grapycal_torch

FROM node:22.9.0-bookworm as frontend-builder

WORKDIR /opt/grapycal

COPY frontend frontend
RUN cd frontend && npm install

COPY .git .git
COPY .gitmodules .gitmodules

COPY submodules/topicsync-client submodules/topicsync-client
RUN cd submodules/topicsync-client && npm install

COPY submodules/objectsync-client submodules/objectsync-client
RUN cd submodules/objectsync-client && npm install

FROM python:3.11-slim-bookworm

WORKDIR /opt/grapycal

COPY scripts/build_frontend.py scripts/build_frontend.py

COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY --from=backend-builder /opt/grapycal/backend backend
COPY --from=backend-builder /opt/grapycal/submodules/topicsync submodules/topicsync
COPY --from=backend-builder /opt/grapycal/submodules/objectsync submodules/objectsync
COPY --from=backend-builder /opt/grapycal/extensions extensions
COPY --from=backend-builder /usr/local/bin /usr/local/bin

COPY --from=frontend-builder /opt/grapycal/frontend frontend
COPY --from=frontend-builder /opt/grapycal/submodules/topicsync-client submodules/topicsync-client
COPY --from=frontend-builder /opt/grapycal/submodules/objectsync-client submodules/objectsync-client

WORKDIR /usr/local/grapycal/workspace/
CMD ["grapycal", "dev", "--host", "0.0.0.0"]

