FROM --platform=linux/amd64 node:lts-alpine3.19 as fbuilder

WORKDIR /lab
COPY frontend ./frontend
COPY submodules/topicsync-client ./submodules/topicsync-client
COPY submodules/objectsync-client ./submodules/objectsync-client
WORKDIR /lab/frontend
RUN npm audit fix
RUN npm install
WORKDIR /lab/submodules/topicsync-client
RUN npm audit fix
RUN npm install
WORKDIR /lab/submodules/objectsync-client
RUN npm audit fix
RUN npm install


FROM --platform=linux/amd64 python:3.11-rc-buster as builder

WORKDIR /lab
COPY backend ./backend
COPY extensions ./extensions
COPY entry ./entry
COPY submodules/topicsync ./submodules/topicsync
COPY submodules/objectsync ./submodules/objectsync

RUN touch README.md
RUN pip install -e submodules/topicsync
RUN pip install -e submodules/objectsync
RUN pip install -e backend
RUN pip install -e extensions/grapycal_builtin


FROM --platform=linux/amd64 python:3.11-rc-slim-buster as runtime

WORKDIR /lab

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /lab /lab
COPY --from=fbuilder /lab /lab
CMD ["python", "entry/run.py", "--backend-path", "backend/src", "--frontend-path", "frontend/dist", "--port", "7943", "--host", "0.0.0.0"]
