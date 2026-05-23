name ?= default

.PHONY: build up shell down logs


build:
	 docker compose --env-file .env.$(name) -p ksef-$(name) build


up:
	 docker compose --env-file .env.$(name) -p ksef-$(name) up -d


shell:
	docker compose -p ksef-$(name) exec ksef-monitor bash


down:
	docker compose -p ksef-$(name) down


logs:
	docker compose -p ksef-$(name) logs -f
