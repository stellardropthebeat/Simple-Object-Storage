FROM python:3.9-slim

WORKDIR /usr/src/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
COPY ./work_queue/worker/compose_w/requirements.txt .
COPY ./work_queue/worker/compose_w/compose.py .
RUN pip install -r requirements.txt
