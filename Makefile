.PHONY: help install seed start-backend start-frontend dev

VENV = .venv
VENV_BIN = $(VENV)/bin

help:
	@echo "Mall Operations Brain Development Commands:"
	@echo "  make install         Create venv and install all python and node.js dependencies"
	@echo "  make seed            Generate and seed synthetic data to Elastic Cloud Serverless"
	@echo "  make start-backend   Start the FastAPI agent server"
	@echo "  make start-frontend  Start the Next.js UI developer server"
	@echo "  make dev             Boot both backend and frontend development servers"

install:
	@echo "Creating virtual environment in $(VENV)..."
	python3 -m venv $(VENV)
	@echo "Installing python dependencies inside virtual environment..."
	$(VENV_BIN)/pip install --upgrade pip
	$(VENV_BIN)/pip install -r data_generator/requirements.txt
	$(VENV_BIN)/pip install -r backend/requirements.txt
	@echo "Installing frontend dependencies..."
	cd frontend && npm install

seed:
	@echo "Running synthetic data seeder using virtual environment..."
	$(VENV_BIN)/python -m data_generator.seeder

start-backend:
	@echo "Starting backend uvicorn server using virtual environment..."
	PYTHONPATH=. $(VENV_BIN)/uvicorn backend.app.main:app --reload --port 8000

start-frontend:
	@echo "Starting Next.js developer server..."
	cd frontend && npm run dev

dev:
	@echo "Starting concurrent development environment..."
	@echo "Please run backend and frontend in separate terminal windows or shells:"
	@echo "  Terminal 1: make start-backend"
	@echo "  Terminal 2: make start-frontend"

