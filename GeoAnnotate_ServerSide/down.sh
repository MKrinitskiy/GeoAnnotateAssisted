#!/bin/bash
# stop docker containers serving GAA server using docker compose

docker compose --env-file=./config/config.env down
