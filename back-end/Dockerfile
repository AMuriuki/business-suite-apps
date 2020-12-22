FROM python:3.6-alpine

RUN adduser -D erp-crm

WORKDIR /home/erp-crm

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY erp-crm.py config.py boot.sh ./
RUN chmod a+x boot.sh

ENV FLASK_APP erp-crm.py

RUN chown -R erp-crm:erp-crm ./
USER erp-crm

EXPOSE 5000
ENTRYPOINT ["./boot.sh"]
