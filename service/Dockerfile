FROM ubuntu:20.04

RUN apt-get update && apt install -y python3-pip sqlite
RUN python3 -m pip install pycryptodome aiosqlite

RUN mkdir /service
WORKDIR /service
RUN mkdir data

COPY fireworx.py crypto.py init.sql run.sh ./

RUN groupadd -g 2000 cryptogroup
RUN useradd -m -u 2001 -g cryptogroup cryptodude

RUN chown -R cryptodude /service
RUN chmod +x fireworx.py run.sh
USER cryptodude

CMD ["/service/run.sh"]
