FROM python:3.9-slim

WORKDIR /usr/src

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apt-get update
RUN apt-get install ffmpeg libsm6 libxext6  -y

RUN pip install --upgrade pip

COPY ./work_queue/worker/extract_w/requirements.txt .
COPY ./work_queue/worker/extract_w/extract.py .
COPY ./work_queue/worker/extract_w/compose.py .

RUN pip install -r requirements.txt
