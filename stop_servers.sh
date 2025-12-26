#!/bin/bash
# stop_servers.sh
# This script stops the server instances using the PIDs saved in servers.pid.

PID_FILE="servers.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "PID file $PID_FILE not found. Are the servers running?"
    exit 1
fi

while read -r pid; do
    if ps -p "$pid" > /dev/null; then
        echo "Stopping process $pid"
        kill "$pid"
    else
        echo "Process $pid not found"
    fi
done < "$PID_FILE"

rm "$PID_FILE"
echo "All servers stopped."

