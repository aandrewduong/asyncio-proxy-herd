import asyncio
import time
import random
import logging
import statistics
import yaml
import argparse

class Benchmark:
    def __init__(self, config_path="config.yml"):
        with open(config_path, "r") as file:
            self.config = yaml.safe_load(file)
        
        self.servers = self.config["ports"]
        self.num_clients = self.config["benchmark"]["num_clients"]
        self.test_duration = self.config["benchmark"]["test_duration"]
        self.timeout = self.config["benchmark"]["timeout"]
        
        logging.basicConfig(
            level=getattr(logging, self.config["logging"]["level"].upper(), logging.INFO),
            filename=self.config["logging"]["filename"],
            format=self.config["logging"]["format"]
        )
        self.logger = logging.getLogger("Benchmark")
        self.latencies = []
        self.requests_sent = 0
        self.errors = 0

    def generate_location(self):
        lat = random.uniform(-90, 90)
        lng = random.uniform(-180, 180)
        return f"{lat:+.6f}{lng:+.6f}"

    async def send_request(self, server, port, message):
        start_time = time.time()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('localhost', port), timeout=self.timeout
            )
            writer.write(message.encode())
            await writer.drain()
            
            # Read response - WHATSAT can be long, so we read until we get enough or timeout
            response_data = []
            while True:
                try:
                    line = await asyncio.wait_for(reader.readline(), timeout=self.timeout)
                    if not line:
                        break
                    response_data.append(line.decode())
                    # For WHATSAT, it ends with double newline or we can just read what's available
                    if not line.strip() and len(response_data) > 1:
                         break
                except asyncio.TimeoutError:
                    break
            
            writer.close()
            await writer.wait_closed()
            
            latency = time.time() - start_time
            return latency, "".join(response_data).strip()
        except Exception as e:
            self.logger.error(f"Error sending request to {server} on port {port}: {e}")
            return None, None

    async def client_worker(self, worker_id, stop_event):
        while not stop_event.is_set():
            server_name = random.choice(list(self.servers.keys()))
            port = self.servers[server_name]
            client_id = f"client{random.randint(1, self.num_clients)}"
            
            # 70% IAMAT, 30% WHATSAT
            if random.random() < 0.7:
                location = self.generate_location()
                message = f"IAMAT {client_id} {location} {time.time()}\n"
            else:
                radius = random.uniform(1, 50)
                bound = random.randint(1, 20)
                message = f"WHATSAT {client_id} {radius} {bound}\n"

            latency, response = await self.send_request(server_name, port, message)
            if latency is not None:
                self.latencies.append(latency)
                self.requests_sent += 1
            else:
                self.errors += 1
            
            # Small sleep to prevent tight loop
            await asyncio.sleep(random.uniform(0.01, 0.1))

    async def run(self, concurrency=10):
        print(f"Starting benchmark for {self.test_duration} seconds with {concurrency} workers...")
        stop_event = asyncio.Event()
        workers = [self.client_worker(i, stop_event) for i in range(concurrency)]
        
        start_time = time.time()
        
        # Run workers
        worker_task = asyncio.gather(*workers)
        
        # Wait for duration
        await asyncio.sleep(self.test_duration)
        stop_event.set()
        
        # Give workers a moment to finish current request
        try:
            await asyncio.wait_for(worker_task, timeout=self.timeout + 1)
        except asyncio.TimeoutError:
            pass
            
        duration = time.time() - start_time
        self.report(duration)

    def report(self, duration):
        avg_latency = statistics.mean(self.latencies) if self.latencies else 0
        max_latency = max(self.latencies) if self.latencies else 0
        min_latency = min(self.latencies) if self.latencies else 0
        rps = self.requests_sent / duration if duration > 0 else 0

        results = [
            f"\nBenchmark Results (Duration: {duration:.2f}s):",
            f"Total Requests Sent: {self.requests_sent}",
            f"Total Errors: {self.errors}",
            f"Requests Per Second: {rps:.2f}",
            f"Average Latency: {avg_latency:.4f} sec",
            f"Max Latency: {max_latency:.4f} sec",
            f"Min Latency: {min_latency:.4f} sec",
        ]

        for line in results:
            self.logger.info(line)
            print(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark for Proxy Herd")
    parser.add_argument("--concurrency", type=int, default=10, help="Number of concurrent workers")
    args = parser.parse_args()

    benchmark = Benchmark()
    asyncio.run(benchmark.run(concurrency=args.concurrency))
