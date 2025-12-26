# Proxy Herd with asyncio

## Description
This project implements a distributed server system using Python's `asyncio` framework to create an "application server herd." The goal is to evaluate `asyncio` as a framework for handling real-time, high-frequency data updates in a decentralized system. The project consists of multiple interconnected servers that process client location updates and respond to queries using the Google Places API.

## Features
- **Distributed Server Communication**: Servers propagate location updates using a simple flooding algorithm.
- **Asynchronous TCP Handling**: Clients communicate with servers via TCP sockets using `asyncio` streams.
- **Google Places API Integration**: Servers fetch nearby place data for clients on request using `aiohttp`.
- **Fault Tolerance**: Servers continue operating even if neighbors disconnect.
- **Logging**: Each server logs its input, output, and connections with persistent file logging.
- **Benchmarking**: Integrated concurrent benchmarking tool to measure RPS and latency.
- **Makefile**: Simplified management for common tasks.

## Project Structure
```
project_root
├── Makefile            # Management commands for install, run, stop, and benchmark
├── benchmark.py        # Concurrent benchmarking script
├── server.py           # Class-based proxy server implementation
├── config.yml          # Configuration (ports, neighbors, logging, API keys)
├── start_servers.sh    # Script to start all servers in background
├── stop_servers.sh     # Script to stop all servers using PID tracking
├── requirements.txt    # Python dependencies
├── README.md           # Project documentation
├── report.pdf          # Research report
└── servers.pid         # Temporary file to track running server processes
```

## Installation
### Prerequisites
- Python 3.11+
- `make` (optional, for simplified commands)

### Steps
1. Clone the repository:
   ```sh
   git clone https://github.com/aandrewduong/asyncio-proxy-herd.git
   cd asyncio-proxy-herd
   ```
2. Install dependencies:
   ```sh
   make install
   # OR: pip install -r requirements.txt
   ```

## Usage
### Managing Servers
Use the provided `Makefile` for easy management:
- **Start Servers**: `make run`
- **Stop Servers**: `make stop`
- **Cleanup Logs**: `make clean`

### Running Benchmarks
The updated benchmark tool supports concurrent workers:
```sh
make benchmark CONCURRENCY=20
# OR: python3 benchmark.py --concurrency 20
```

### Server Commands
- **IAMAT**: Clients send location updates to the server.
  ```
  IAMAT <client_id> <latitude+longitude> <timestamp>
  ```
- **WHATSAT**: Clients request nearby places based on a client's last known location.
  ```
  WHATSAT <client_id> <radius_km> <max_results>
  ```
- **AT**: Internal message format for propagating location updates between servers.
  ```
  AT <server_id> <time_diff> <client_id> <latitude+longitude> <timestamp>
  ```

### Manual Testing
You can manually connect to a server using `nc` or `telnet`:
```sh
nc localhost 10099
```
Then type a command:
```
IAMAT client1 +34.068930-118.445127 1621464827.95
```

## Configuration
The `config.yml` file contains:
- **Server Ports**: Mapping of server names to their respective ports.
- **Neighbor Relationships**: Defines the network topology.
- **API Key**: Google Places API key.
- **Benchmarking**: Configures default test parameters.
- **Logging**: Specifies log level and format.

## Research Report
The research [report](report.pdf) provides an in-depth analysis of `asyncio` as a framework for this architecture, evaluating performance, maintainability, and comparison with other asynchronous frameworks.
