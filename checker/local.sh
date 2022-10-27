#!/bin/sh

docker-compose up -d fireworx-mongo

pushd src
export MONGO_ENABLED=1
export MONGO_HOST=localhost
export MONGO_PORT=1814
export MONGO_USER=fireworx_checker
export MONGO_PASSWORD=fireworx_checker
gunicorn -c gunicorn.conf.py checker:app
