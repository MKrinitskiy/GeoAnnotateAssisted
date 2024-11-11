#!/bin/bash
# build docker image

docker build -t geoseg-server:latest -f Dockerfile2 .
