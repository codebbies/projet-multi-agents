FROM python:3.12-slim

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY tsp_tools.py /opt/tools/tsp_tools.py
ENV PYTHONPATH=/opt/tools

RUN useradd --create-home --shell /bin/bash executor
USER executor

WORKDIR /workspace
