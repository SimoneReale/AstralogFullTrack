import paho.mqtt.client as mqtt
import ssl
import uuid
import time
import argparse
import os

# --- MISSION CONFIGURATION ---
BROKER_URL = ""
PORT = 8883
TOPIC = "esa/astralog/telemetry"
USER = "students"
PASSWORD = "Listeningstuff26"
OUTPUT_DIR = "collector_output"

class TelemetryCollector:
    def __init__(self, mode, limit):
        self.mode = mode  # 'count' or 'time'
        self.limit = limit
        self.buffer = []
        self.last_flush_time = time.time() * 1000 # ms

    def flush(self):
        if not self.buffer:
            return
        
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
        
        timestamp = int(time.time())
        filename = os.path.join(OUTPUT_DIR, f"raw_data_{timestamp}.txt")
        
        with open(filename, "w") as f:
            f.write("\n".join(self.buffer))
        
        print(f"### Buffered data saved to {filename} ({len(self.buffer)} messages)")
        self.buffer = []
        self.last_flush_time = time.time() * 1000

    def handle_message(self, payload):
        self.buffer.append(payload)
        current_time = time.time() * 1000

        if self.mode == "count" and len(self.buffer) >= self.limit:
            self.flush()
        elif self.mode == "time" and (current_time - self.last_flush_time) >= self.limit:
            self.flush()

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"CONNECTED to {BROKER_URL}")
        client.subscribe(TOPIC)
    else:
        print(f"CONNECTION ERROR: {rc}")

def on_message(client, userdata, msg):
    raw_payload = msg.payload.decode('utf-8')
    collector = userdata['collector']
    collector.handle_message(raw_payload)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AstraLog Telemetry Collector")
    parser.add_argument("--mode", choices=["count", "time"], required=True, help="Accumulation mode")
    parser.add_argument("--limit", type=int, required=True, help="Messages count or Time interval in ms")
    args = parser.parse_args()

    collector = TelemetryCollector(args.mode, args.limit)
    client_id = f"Station_{uuid.uuid4().hex[:6]}"

    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id, protocol=mqtt.MQTTv5, userdata={'collector': collector})
    except:
        client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5, userdata={'collector': collector})

    client.username_pw_set(USER, PASSWORD)
    client.tls_set_context(ssl.create_default_context())
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"### Starting {args.mode}-based receiver (Limit: {args.limit})")
    client.connect(BROKER_URL, PORT)
    client.loop_forever()