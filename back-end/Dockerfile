FROM python:3.6-alpine

RUN adduser -D teleios

WORKDIR /home/teleios

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY teleios.py config.py boot.sh ./
RUN chmod a+x boot.sh

ENV FLASK_APP teleios.py

RUN chown -R teleios:teleios ./
USER teleios

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
