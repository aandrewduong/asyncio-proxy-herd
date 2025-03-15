# Proxy Herd with asyncio

## Description
This project implements a distributed server system using Python's `asyncio` framework to create an "application server herd." The goal is to evaluate `asyncio` as a framework for handling real-time, high-frequency data updates in a decentralized system. The project consists of multiple interconnected servers that process client location updates and respond to queries using the Google Places API.

## Features
- **Distributed Server Communication**: Servers propagate location updates using a simple flooding algorithm.
- **Asynchronous TCP Handling**: Clients communicate with servers via TCP sockets.
- **Google Places API Integration**: Servers fetch nearby place data for clients on request.
- **Fault Tolerance**: Servers continue operating even if neighbors disconnect.
- **Logging**: Each server logs its input, output, and connections.

## Project Structure
```
📦 project_root
├── 📜 benchmark.py        # Benchmarking script to measure server performance
├── 📜 server.py           # Main server implementation
├── 📜 config.yml          # Configuration file (ports, neighbors, logging, API keys)
├── 📜 start_servers.sh    # Script to start all servers
├── 📜 README.md           # Project documentation
├── 📜 report.pdf          # Research report analyzing asyncio's suitability for this architecture
```

## Installation
### Prerequisites
- Python 3.11.2
- `aiohttp` library
- `pyyaml` library

### Steps
1. Clone the repository:
   ```sh
   git clone https://github.com/aandrewduong/asyncio-proxy-herd.git
   cd asyncio-proxy-herd
   ```
2. Start the servers:
   ```sh
   ./start_servers.sh
   ```
3. Run the benchmark tool:
   ```sh
   python3 benchmark.py
   ```

## Configuration
The `config.yml` file contains:
- **Server Ports**: Mapping of server names to their respective ports.
- **Neighbor Relationships**: Defines how servers communicate with each other.
- **Benchmarking**: Configures test parameters such as number of clients, test duration, and timeout.
- **Logging**: Specifies log level, filename, and format.

Example `config.yml` snippet:
```yaml
benchmark:
  num_clients: 5
  test_duration: 5  # in seconds
  timeout: 2  # in seconds
logging:
  level: "INFO"
  filename: "benchmark.log"
  format: "%(asctime)s - %(levelname)s - %(message)s"
```

## Usage
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
- **Invalid Command Response**: Servers return:
  ```
  ? <invalid_command>
  ```

### Example
Client sends:
```
IAMAT kiwi.cs.ucla.edu +34.068930-118.445127 1621464827.959498503
```
Server responds:
```
AT Clark +0.263873386 kiwi.cs.ucla.edu +34.068930-118.445127 1621464827.959498503
```

### WHATSAT Example
Client requests nearby places:
```
WHATSAT kiwi.cs.ucla.edu 10 5
```
Server responds with:
```
AT Clark +0.263873386 kiwi.cs.ucla.edu +34.068930-118.445127 1621464827.959498503
{
   "results": [
      { "name": "Place 1", "vicinity": "Location 1" },
      { "name": "Place 2", "vicinity": "Location 2" }
   ]
}
```

## Connecting to the Server
You can manually connect to a server using `nc` (Netcat) or `telnet`. This allows you to send test commands and observe server responses.

### Using `nc` (Netcat)
Netcat is a simple way to establish a TCP connection with a server.

1. Find the server's port from `config.yml`.
2. Run the following command in your terminal:
   ```sh
   nc <server_host> <server_port>
   ```
   Example:
   ```sh
   nc localhost 5000
   ```
3. Send commands by typing them and pressing Enter. For example:
   ```
   IAMAT kiwi.cs.ucla.edu +34.068930-118.445127 1621464827.959498503
   ```
   The server should respond with an `AT` message.

### Using `telnet`
Telnet can also be used to connect to the server.

1. Run the following command:
   ```sh
   telnet <server_host> <server_port>
   ```
   Example:
   ```sh
   telnet localhost 5000
   ```
2. Enter commands just like in the Netcat example.

These methods are useful for debugging and testing server communication.

## Benchmarking
Run the benchmark tool to measure server latency:
```
python3 benchmark.py
```

## Research Report
The research [report](https://github.com/aandrewduong/asyncio-proxy-herd/blob/main/report.pdf) provides an in-depth analysis of `asyncio` as a framework for this architecture. It evaluates performance, maintainability, type safety, and comparisons with other asynchronous frameworks such as Node.js. The report also discusses Python's concurrency model, memory management, and suitability for large-scale distributed systems.

