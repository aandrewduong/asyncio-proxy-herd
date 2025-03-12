import asyncio
import aiohttp
import time
import random
import logging
import statistics
import yaml

# Load config.yml
with open("config.yml", "r") as file:
    config = yaml.safe_load(file)

# Configuration from YAML
SERVERS = config["ports"]
NUM_CLIENTS = config["benchmark"]["num_clients"]
TEST_DURATION = config["benchmark"]["test_duration"]
TIMEOUT = config["benchmark"]["timeout"]

# Setup logging from YAML
logging.basicConfig(
    level=getattr(logging, config["logging"]["level"].upper(), logging.INFO),
    filename=config["logging"]["filename"],
    format=config["logging"]["format"]
)

def generate_location():
    """Generates a valid ISO 6709 location string."""
    lat = random.uniform(-90, 90)
    lng = random.uniform(-180, 180)
    return f"{lat:+.6f}{lng:+.6f}"

async def send_request(server, port, message):
    start_time = time.time()
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection('localhost', port), timeout=TIMEOUT)
        writer.write(message.encode())
        await writer.drain()
        response = await asyncio.wait_for(reader.read(1024), timeout=TIMEOUT)
        writer.close()
        await writer.wait_closed()
        latency = time.time() - start_time
        return latency, response.decode().strip()
    except Exception as e:
        logging.error(f"Error sending request to {server} on port {port}: {e}")
        return None, None

async def benchmark():
    latencies = []
    requests_sent = 0
    start_time = time.time()

    while time.time() - start_time < TEST_DURATION:
        server = random.choice(list(SERVERS.keys()))
        port = SERVERS[server]
        client_id = f"client{random.randint(1, NUM_CLIENTS)}"
        location = generate_location()
        timestamp = time.time()
        message = f"IAMAT {client_id} {location} {timestamp}\n"
        
        latency, response = await send_request(server, port, message)
        if latency:
            latencies.append(latency)
            requests_sent += 1

    avg_latency = statistics.mean(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0

    logging.info("Benchmark Results:")
    logging.info(f"Total Requests Sent: {requests_sent}")
    logging.info(f"Average Latency: {avg_latency:.4f} sec")
    logging.info(f"Max Latency: {max_latency:.4f} sec")
    logging.info(f"Min Latency: {min_latency:.4f} sec")

    print(f"Total Requests Sent: {requests_sent}")
    print(f"Average Latency: {avg_latency:.4f} sec")
    print(f"Max Latency: {max_latency:.4f} sec")
    print(f"Min Latency: {min_latency:.4f} sec")

if __name__ == "__main__":
    asyncio.run(benchmark())