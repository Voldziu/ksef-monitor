# 1. For each NIP make a `.env.{name}' file
# 2. How to run:

- Then run: docker compose -p ksef-{name} --env-file .env.{name} up -d
# 3. then, use docker compose -p ksef-{name} before any docker compose command



# Makefile usage

- make build name={name}
- make up name={name}
- make shell name={name}
...