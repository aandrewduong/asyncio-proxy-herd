#!/bin/bash
# start_servers.sh
# This script starts the five server instances for Bailey, Bona, Campbell, Clark, and Jaquez.
# It saves the PIDs to a file for easy stopping.

SERVERS=("Bailey" "Bona" "Campbell" "Clark" "Jaquez")
PID_FILE="servers.pid"

# Clear old PID file if it exists
> "$PID_FILE"

for server in "${SERVERS[@]}"; do
    echo "Starting server: $server"
    nohup python3 server.py "$server" > "server_${server}.out" 2>&1 &
    PID=$!
    echo "$PID" >> "$PID_FILE"
    echo "Started $server with PID $PID"
done

echo "All servers started. PIDs saved to $PID_FILE."
