import asyncio
import aiohttp
import time
import sys
import logging
import json
import re
import yaml

# Load configuration from config.yml
with open("config.yml", "r") as config_file:
    config = yaml.safe_load(config_file)

PORTS = config["ports"]
NEIGHBORS = config["neighbors"]
API_KEY = config["api_key"]

client_data = {}

# Regex to parse ISO 6709 location strings
location_regex = re.compile(r'^([+-]\d+\.\d+)([+-]\d+\.\d+)$')

# Ensure a valid server name is provided
if len(sys.argv) < 2 or sys.argv[1] not in PORTS:
    sys.stderr.write("Usage: python3 server.py <ServerName>\nValid names: " + ", ".join(PORTS.keys()) + "\n")
    sys.exit(1)

SERVER_NAME = sys.argv[1]
SERVER_PORT = PORTS[SERVER_NAME]

logging.basicConfig(
    level=logging.INFO,
    filename=f"server_{SERVER_NAME}.log",
    format="%(asctime)s %(message)s",
)

def log(message: str) -> None:
    logging.info(message)

def parse_location(loc_str: str):
    match = location_regex.match(loc_str)
    return match.groups() if match else (None, None)

async def propagate(message: str, exclude: set):
    for neighbor in NEIGHBORS.get(SERVER_NAME, []):
        if neighbor in exclude:
            continue
        try:
            reader, writer = await asyncio.open_connection('localhost', PORTS[neighbor])
            writer.write(message.encode())
            await writer.drain()
            writer.close()
            await writer.wait_closed()
        except Exception as e:
            log(f"Error propagating to {neighbor}: {e}")


async def handle_AT(tokens: list, writer: asyncio.StreamWriter):
    if len(tokens) != 6:
        await send_invalid(" ".join(tokens), writer)
        return

    # Unpack fields
    server_id = tokens[1]
    time_diff_str = tokens[2]        # e.g., "+0.263873386"
    client_id = tokens[3]
    location = tokens[4]            # e.g., "+34.068930-118.445127"
    client_time_str = tokens[5]     # e.g., "1621464827.959498503"

    # Validate that client_time_str is float-like
    try:
        client_time = float(client_time_str)
    except ValueError:
        await send_invalid(" ".join(tokens), writer)
        return

    # If this is a newer update than we’ve seen before, store and flood it.
    # client_data stores: client_id -> (AT_message_string, client_time)
    if client_id not in client_data or client_time > client_data[client_id][1]:
        # Reconstruct the full AT message to store/propagate
        full_message = " ".join(tokens) + "\n"
        client_data[client_id] = (full_message.strip(), client_time)

        # Flood the update to neighbors, excluding the original sender to prevent loops
        asyncio.create_task(propagate(full_message, exclude={server_id}))

    # Note: We do NOT send a direct response back to whoever sent the AT.
    # AT messages are purely for server-to-server updates.

async def handle_IAMAT(tokens: list, writer: asyncio.StreamWriter):
    if len(tokens) != 4:
        await send_invalid(" ".join(tokens), writer)
        return

    client_id, location, client_time_str = tokens[1], tokens[2], tokens[3]
    try:
        client_time = float(client_time_str)
    except ValueError:
        await send_invalid(" ".join(tokens), writer)
        return

    now = time.time()
    time_diff = now - client_time
    response = f"AT {SERVER_NAME} {time_diff:+f} {client_id} {location} {client_time_str}\n"
    log(f"Processed IAMAT for {client_id}: {response.strip()}")

    if client_id not in client_data or client_time > client_data[client_id][1]:
        client_data[client_id] = (response.strip(), client_time)
        asyncio.create_task(propagate(response, exclude=set()))

    writer.write(response.encode())
    await writer.drain()

async def handle_WHATSAT(tokens: list, writer: asyncio.StreamWriter):
    if len(tokens) != 4:
        await send_invalid(" ".join(tokens), writer)
        return

    client_id = tokens[1]
    try:
        radius = float(tokens[2])
        bound = int(tokens[3])
    except ValueError:
        await send_invalid(" ".join(tokens), writer)
        return

    if radius > 50 or bound > 20 or client_id not in client_data:
        await send_invalid(" ".join(tokens), writer)
        return

    update, _ = client_data[client_id]
    parts = update.split()
    location = parts[4]
    lat, lng = parse_location(location)
    if lat is None or lng is None:
        await send_invalid(" ".join(tokens), writer)
        return

    places_url = "https://places.googleapis.com/v1/places:searchNearby"
    payload = {
        "maxResultCount": bound,
        "locationRestriction": {"circle": {"center": {"latitude": float(lat), "longitude": float(lng)}, "radius": radius * 1000}}
    }
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": API_KEY, "X-Goog-FieldMask": "*"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(places_url, headers=headers, json=payload) as resp:
            places_data = await resp.json()

    places_data["results"] = places_data.get("results", [])[:bound]
    json_data = json.dumps(places_data, indent=4)
    response = f"{update}\n{json_data}\n\n"
    writer.write(response.encode())
    await writer.drain()

async def send_invalid(command: str, writer: asyncio.StreamWriter):
    writer.write(f"? {command}\n".encode())
    await writer.drain()
    log(f"Sent error response for invalid command: {command}")

async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info("peername")
    log(f"New connection from {addr}")
    try:
        while not reader.at_eof():
            data = await reader.readline()
            if not data:
                break
            message = data.decode().strip()
            log(f"Received: {message} from {addr}")
            tokens = message.split()
            if not tokens:
                continue
            command = tokens[0]
            if command == "AT":
                await handle_AT(tokens, writer)
            elif command == "IAMAT":
                await handle_IAMAT(tokens, writer)
            elif command == "WHATSAT":
                await handle_WHATSAT(tokens, writer)
            else:
                await send_invalid(message, writer)
    finally:
        writer.close()
        await writer.wait_closed()
        log(f"Closed connection from {addr}")

async def main():
    server = await asyncio.start_server(handle_connection, 'localhost', SERVER_PORT)
    log(f"{SERVER_NAME} serving on port {SERVER_PORT}")
    async with server:
        await server.serve_forever()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Server shutting down.")
