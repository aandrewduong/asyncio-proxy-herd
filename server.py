import asyncio
import aiohttp
import time
import sys
import logging
import json
import re
import yaml

class ProxyServer:
    def __init__(self, name, config):
        self.name = name
        self.config = config
        self.port = config["ports"][name]
        self.neighbors = config["neighbors"].get(name, [])
        self.api_key = config["api_key"]
        self.client_data = {}  # client_id -> (AT_message_string, client_time)
        self.location_regex = re.compile(r'^([+-]\d+\.\d+)([+-]\d+\.\d+)$')
        
        logging.basicConfig(
            level=logging.INFO,
            filename=f"server_{self.name}.log",
            format="%(asctime)s %(levelname)s: %(message)s",
        )
        self.logger = logging.getLogger(self.name)

    def log(self, message: str, level=logging.INFO) -> None:
        self.logger.log(level, message)

    def parse_location(self, loc_str: str):
        match = self.location_regex.match(loc_str)
        return match.groups() if match else (None, None)

    async def propagate(self, message: str, exclude: set):
        for neighbor in self.neighbors:
            if neighbor in exclude:
                continue
            try:
                reader, writer = await asyncio.open_connection('localhost', self.config["ports"][neighbor])
                writer.write(message.encode())
                await writer.drain()
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                self.log(f"Error propagating to {neighbor}: {e}", level=logging.ERROR)

    async def handle_AT(self, tokens: list, writer: asyncio.StreamWriter):
        if len(tokens) != 6:
            await self.send_invalid(" ".join(tokens), writer)
            return

        server_id = tokens[1]
        client_id = tokens[3]
        client_time_str = tokens[5]

        try:
            client_time = float(client_time_str)
        except ValueError:
            await self.send_invalid(" ".join(tokens), writer)
            return

        if client_id not in self.client_data or client_time > self.client_data[client_id][1]:
            full_message = " ".join(tokens) + "\n"
            self.client_data[client_id] = (full_message.strip(), client_time)
            asyncio.create_task(self.propagate(full_message, exclude={server_id}))

    async def handle_IAMAT(self, tokens: list, writer: asyncio.StreamWriter):
        if len(tokens) != 4:
            await self.send_invalid(" ".join(tokens), writer)
            return

        client_id, location, client_time_str = tokens[1], tokens[2], tokens[3]
        try:
            client_time = float(client_time_str)
        except ValueError:
            await self.send_invalid(" ".join(tokens), writer)
            return

        now = time.time()
        time_diff = now - client_time
        response = f"AT {self.name} {time_diff:+f} {client_id} {location} {client_time_str}\n"
        self.log(f"Processed IAMAT for {client_id}: {response.strip()}")

        if client_id not in self.client_data or client_time > self.client_data[client_id][1]:
            self.client_data[client_id] = (response.strip(), client_time)
            asyncio.create_task(self.propagate(response, exclude=set()))

        writer.write(response.encode())
        await writer.drain()

    async def handle_WHATSAT(self, tokens: list, writer: asyncio.StreamWriter):
        if len(tokens) != 4:
            await self.send_invalid(" ".join(tokens), writer)
            return

        client_id = tokens[1]
        try:
            radius = float(tokens[2])
            bound = int(tokens[3])
        except ValueError:
            await self.send_invalid(" ".join(tokens), writer)
            return

        if radius > 50 or bound > 20 or client_id not in self.client_data:
            await self.send_invalid(" ".join(tokens), writer)
            return

        update, _ = self.client_data[client_id]
        parts = update.split()
        location = parts[4]
        lat, lng = self.parse_location(location)
        if lat is None or lng is None:
            await self.send_invalid(" ".join(tokens), writer)
            return

        places_url = "https://places.googleapis.com/v1/places:searchNearby"
        payload = {
            "maxResultCount": bound,
            "locationRestriction": {"circle": {"center": {"latitude": float(lat), "longitude": float(lng)}, "radius": radius * 1000}}
        }
        headers = {"Content-Type": "application/json", "X-Goog-Api-Key": self.api_key, "X-Goog-FieldMask": "*"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(places_url, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        places_data = await resp.json()
                        places_data["results"] = places_data.get("results", [])[:bound]
                        json_data = json.dumps(places_data, indent=4)
                        response = f"{update}\n{json_data}\n\n"
                        writer.write(response.encode())
                        await writer.drain()
                    else:
                        self.log(f"Google Places API error: {resp.status}", level=logging.ERROR)
                        await self.send_invalid(" ".join(tokens), writer)
        except Exception as e:
            self.log(f"Exception during WHATSAT: {e}", level=logging.ERROR)
            await self.send_invalid(" ".join(tokens), writer)

    async def send_invalid(self, command: str, writer: asyncio.StreamWriter):
        writer.write(f"? {command}\n".encode())
        await writer.drain()
        self.log(f"Sent error response for invalid command: {command}", level=logging.WARNING)

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        self.log(f"New connection from {addr}")
        try:
            while not reader.at_eof():
                data = await reader.readline()
                if not data:
                    break
                message = data.decode().strip()
                self.log(f"Received: {message} from {addr}")
                tokens = message.split()
                if not tokens:
                    continue
                command = tokens[0]
                if command == "AT":
                    await self.handle_AT(tokens, writer)
                elif command == "IAMAT":
                    await self.handle_IAMAT(tokens, writer)
                elif command == "WHATSAT":
                    await self.handle_WHATSAT(tokens, writer)
                else:
                    await self.send_invalid(message, writer)
        except Exception as e:
            self.log(f"Connection error with {addr}: {e}", level=logging.ERROR)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            self.log(f"Closed connection from {addr}")

    async def run(self):
        server = await asyncio.start_server(self.handle_connection, 'localhost', self.port)
        self.log(f"Serving on port {self.port}")
        async with server:
            await server.serve_forever()

if __name__ == '__main__':
    with open("config.yml", "r") as config_file:
        config = yaml.safe_load(config_file)

    if len(sys.argv) < 2 or sys.argv[1] not in config["ports"]:
        sys.stderr.write("Usage: python3 server.py <ServerName>\nValid names: " + ", ".join(config["ports"].keys()) + "\n")
        sys.exit(1)

    server_name = sys.argv[1]
    proxy_server = ProxyServer(server_name, config)
    try:
        asyncio.run(proxy_server.run())
    except KeyboardInterrupt:
        proxy_server.log("Server shutting down.")
