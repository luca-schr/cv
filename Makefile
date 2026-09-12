.PHONY: run build

VENV := .venv/bin
HOST ?= 127.0.0.1
PORT ?= 8000

run:
	@test -x $(VENV)/uvicorn || { echo "Crée le venv : python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }
	$(VENV)/uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

build:
	cd client && npm run build
