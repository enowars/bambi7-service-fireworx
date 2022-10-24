#!/bin/sh

touch data/db.sqlite
sqlite3 data/db.sqlite < init.sql

python3 /service/app.py
