.DEFAULT: help
.PHONY: help build push login

IMAGE_NAME=omnikdataloggerproxy
IMAGE_TAG?=latest
DOCKER_USER?=$(shell read -s -p "Docker username:"$$'\n' usr; echo $$usr)
DOCKER_PASS?=$(shell read -s -p "Docker password:"$$'\n' pwd; echo $$pwd)

help: ## This help.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# DOCKER TASKS
build: ## Build the Docker image. Use IMAGE_TAG to specify tag (default:latest)
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) .

push: login build ## Tag and push to Docker Hub
	@docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(DOCKER_USER)/$(IMAGE_NAME):$(IMAGE_TAG)
	@docker push $(DOCKER_USER)/$(IMAGE_NAME):$(IMAGE_TAG)

login: ## Login to Docker Hub
	$(info Login to Docker Hub with username "${DOCKER_USER}" (Username not correct? Press CTRL-C now.))
	@echo $(DOCKER_PASS) | docker login -u $(DOCKER_USER) --password-stdin 