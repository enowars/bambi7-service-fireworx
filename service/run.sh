#!/bin/sh

touch /service/data/db.sqlite
sqlite3 /service/data/db.sqlite < init.sql

python3 /service/app.py
