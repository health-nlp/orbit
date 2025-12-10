# .PHONY: all api data
# all: data api

# data:
# 	docker build --platform=linux/amd64 -f Dockerfile.data -t openpm-data:latest .
# 	docker run --platform=linux/amd64 --mount type=bind,source=${PWD}/app,target=/app/ openpm-data:latest

# api: 
# 	docker build --platform=linux/amd64 -f Dockerfile.api -t openpm-api:latest .
# 	docker run -p 8000:8000 --platform=linux/amd64 --mount type=bind,source=${PWD}/app,target=/app/ openpm-api:latest 

.PHONY up down logs

all: up

up: 
	@echo "Starting openpm-system: Building, indexing and starting API ..."
	docker compose up --build -d

down: 
	@echo "Stopping and cleaning up all services ..."
	docker compose down

logs:
	@echo "Showing log-output in realtime (CTRL+C to end process)..."
	docker compose logs -f