FROM --platform=linux/amd64 node:lts-alpine3.19 as fbuilder

WORKDIR /minilab
COPY frontend ./frontend
COPY submodules/topicsync-client ./submodules/topicsync-client
COPY submodules/objectsync-client ./submodules/objectsync-client
WORKDIR /minilab/frontend
RUN npm audit fix
RUN npm install
WORKDIR /minilab/submodules/topicsync-client
RUN npm audit fix
RUN npm install
WORKDIR /minilab/submodules/objectsync-client
RUN npm audit fix
RUN npm install


FROM --platform=linux/amd64 python:3.11-rc-buster as builder

WORKDIR /minilab
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

WORKDIR /minilab

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /minilab /minilab
COPY --from=fbuilder /minilab /minilab
CMD ["python", "entry/run.py", "--backend-path", "backend/src", "--frontend-path", "frontend/dist", "--port", "7943", "--host", "0.0.0.0"]
