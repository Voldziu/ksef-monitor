name ?=
.PHONY: build up shell down logs
ifeq ($(name),)
    env_file = .env
    project_name = ksef
else
    env_file = .env.$(name)
    project_name = ksef-$(name)
endif

COMPOSE_CMD = docker compose --env-file $(env_file) -p $(project_name)

build:
	ENV_FILE=$(env_file) $(COMPOSE_CMD) build

up:
	ENV_FILE=$(env_file) $(COMPOSE_CMD) up -d

shell:
	$(COMPOSE_CMD) exec ksef-monitor bash

down:
	$(COMPOSE_CMD) down

logs:
	$(COMPOSE_CMD) logs ksef-monitor -f