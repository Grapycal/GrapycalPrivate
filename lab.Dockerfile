FROM --platform=linux/amd64 python:3.11-rc-buster as builder

WORKDIR /lab
COPY . .
RUN python install.py

FROM --platform=linux/amd64 python:3.11-rc-slim-buster as runtime

WORKDIR /lab

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /lab /lab

CMD ["python", "-m", "grapycal.entry.run", "--frontend-path", "frontend", "--port", "7943", "--host", "0.0.0.0"]
