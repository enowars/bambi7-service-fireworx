#!/bin/sh

touch /service/data/db.sqlite
sqlite3 /service/data/db.sqlite < init.sql

while true; do
	sqlite3 /service/data/db.sqlite \
		"PRAGMA foreign_keys = ON; \
		DELETE FROM users WHERE delet < strftime('%s', 'now')"
	sleep 60
done &

python3 /service/app.py
