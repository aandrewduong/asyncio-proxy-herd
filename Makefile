# Variables
PYTHON = python3
PIP = $(PYTHON) -m pip
SERVER_SCRIPT = server.py
BENCHMARK_SCRIPT = benchmark.py
START_SCRIPT = ./start_servers.sh
STOP_SCRIPT = ./stop_servers.sh
PID_FILE = servers.pid

.PHONY: all install run stop benchmark clean help

all: help

install: ## Install required dependencies
	$(PIP) install -r requirements.txt

run: ## Start all proxy servers
	@echo "Starting servers..."
	@$(START_SCRIPT)

stop: ## Stop all proxy servers
	@echo "Stopping servers..."
	@$(STOP_SCRIPT)

benchmark: ## Run the benchmark (use CONCURRENCY=N to set workers)
	$(PYTHON) $(BENCHMARK_SCRIPT) --concurrency $(or $(CONCURRENCY),10)

clean: ## Remove log files and output files
	rm -f *.log *.out $(PID_FILE)
	@echo "Cleaned up logs and PID files."

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

