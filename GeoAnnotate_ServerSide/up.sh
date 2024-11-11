#!/bin/bash
# start docker containers serving GAA server using docker compose

docker compose --env-file=./config/config.env up -d
docker exec gaa-server service ssh start
