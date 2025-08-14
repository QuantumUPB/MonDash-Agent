PYTHON ?= python3

run:
	$(PYTHON) mondash-agent.py

# Install Python dependencies
install:
	$(PYTHON) -m pip install -r requirements.txt

# Build and run the container using docker compose
compose-up:
	docker compose up --build

zip:
	zip -r agent.zip . -x '*.git*'
