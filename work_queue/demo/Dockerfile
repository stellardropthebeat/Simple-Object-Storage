FROM python:3.10-slim-buster

WORKDIR /usr/src/

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip
COPY ../worker/requirements.txt .
RUN pip install -r requirements.txt

#RUN mkdir /usr/src/logs
#RUN touch /usr/src/logs/worker01.log

COPY tasks.py .