#!/bin/sh
touch data/store.db
sqlite3 data/store.db < init_client.sql
#socat TCP4-LISTEN:9122,fork,reuseaddr EXEC:'python3 /service/cry.py'
python3 /service/fireworx.py
