FROM python:3.12-slim

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN useradd --create-home --shell /bin/bash executor
USER executor

WORKDIR /workspace
