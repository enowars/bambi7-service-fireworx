FROM ubuntu:22.04

RUN apt-get update && apt install -y python3-pip sqlite sudo

WORKDIR /tmp
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

WORKDIR /service
RUN mkdir data
COPY static static
COPY app.py crypto.py init.sql entrypoint.sh ./

RUN useradd -u 2000 cryptodude
RUN chmod +x entrypoint.sh

ENTRYPOINT /service/entrypoint.sh
