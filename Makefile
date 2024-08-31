.PHONY: build run

APP=postgres-performance-insights-exporter
IMAGE_NAME = andriik/$(APP)
IMAGE_VERSION = latest

docker-build:
	docker build -t $(IMAGE_NAME):$(IMAGE_VERSION) .
docker-run:
	docker run --network host --rm --name $(APP) $(IMAGE_NAME):$(IMAGE_VERSION)
