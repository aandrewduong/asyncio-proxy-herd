#!/bin/bash
# start_servers.sh
# This script starts the five server instances for Bailey, Bona, Campbell, Clark, and Jaquez.
# Each server's output is saved to a file named server_<ServerName>.out.

SERVERS=("Bailey" "Bona" "Campbell" "Clark" "Jaquez")

for server in "${SERVERS[@]}"; do
    echo "Starting server: $server"
    nohup python3 server.py "$server" > "server_${server}.out" 2>&1 &
    echo "Started $server with PID $!"
done

echo "All servers started."