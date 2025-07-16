.PHONY: all api data
all: data api

data:
	docker build --platform=linux/amd64 -f Dockerfile.data -t openpm-data:latest .
	docker run --platform=linux/amd64 --mount type=bind,source=${PWD}/app,target=/app/ openpm-data:latest

api: 
	docker build --platform=linux/amd64 -f Dockerfile.api -t openpm-api:latest .
	docker run --platform=linux/amd64 --mount type=bind,source=${PWD}/app,target=/app/ openpm-api:latest