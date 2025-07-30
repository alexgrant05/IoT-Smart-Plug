import re
import socket
import threading
import time


class UDPHandler:
    """Handles UDP communication with ESP32"""

    def __init__(self, port=3333, data_callback=None, connection_callback=None):
        self.port = port
        self.data_callback = data_callback
        self.connection_callback = connection_callback

        self.socket = None
        self.running = False
        self.thread = None
        self.last_data_time = 0
        self._lock = threading.Lock()

    def start(self):
        """Start the UDP listener"""
        with self._lock:
            if self.running:
                return

            self.running = True
            self.thread = threading.Thread(target=self._listen, daemon=True)
            self.thread.start()
            print(f"[UDP] Started listener on port {self.port}")

    def stop(self):
        """Stop the UDP listener"""
        with self._lock:
            self.running = False

        if self.socket:
            try:
                # Create a dummy socket to unblock the listening socket
                dummy_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                dummy_sock.sendto(b"STOP", ("127.0.0.1", self.port))
                dummy_sock.close()
            except:
                pass

            try:
                self.socket.close()
            except:
                pass

        if self.thread:
            self.thread.join(timeout=2)
        print("[UDP] Listener stopped")

    def _listen(self):
        """Main listening loop with improved parsing"""
        # Add startup delay
        time.sleep(2)

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Platform-specific socket options
            try:
                # Linux/Mac
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except AttributeError:
                # Windows doesn't have SO_REUSEPORT
                pass

            self.socket.bind(("", self.port))
            self.socket.settimeout(2.0)

            print(f"[UDP] Listening on all interfaces, port {self.port}")

            if self.connection_callback:
                self.connection_callback(f"Listening on port {self.port}")

            # Send discovery broadcast
            self._send_discovery()

            consecutive_errors = 0
            max_errors = 5

            while True:
                # Check if we should stop
                with self._lock:
                    if not self.running:
                        break

                try:
                    data, addr = self.socket.recvfrom(1024)

                    # Skip stop messages
                    if data == b"STOP":
                        continue

                    message = data.decode("utf-8", errors="ignore").strip()

                    consecutive_errors = 0
                    self.last_data_time = time.time()

                    print(f"[UDP] Received from {addr[0]}: {message}")

                    # Parse power data with improved logic
                    power_value = self._parse_power_message(message)

                    if power_value is not None:
                        if self.data_callback:
                            self.data_callback(power_value, addr[0])

                        if self.connection_callback:
                            self.connection_callback(
                                f"Connected to {addr[0]} - Live data", addr[0]
                            )

                    elif message.startswith("status:"):
                        status = message.split(":", 1)[1].strip()
                        print(f"[ESP32] Status: {status}")
                        if self.connection_callback:
                            self.connection_callback(f"ESP32 Status: {status}")

                    else:
                        print(f"[UDP] Unknown message format: {message}")

                except socket.timeout:
                    continue
                except UnicodeDecodeError as e:
                    print(f"[UDP] Unicode decode error: {e}")
                    consecutive_errors += 1
                except Exception as e:
                    with self._lock:
                        if not self.running:
                            break

                    consecutive_errors += 1
                    print(f"[UDP] Error ({consecutive_errors}/{max_errors}): {e}")

                    if consecutive_errors >= max_errors:
                        print("[UDP] Too many errors, restarting...")
                        break
                    time.sleep(1)

        except Exception as e:
            print(f"[UDP] Listener failed: {e}")
        finally:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
            print("[UDP] Listener thread ended")

    def _parse_power_message(self, message):
        """Parse power message with multiple format support"""
        try:
            # Format 1: "power:123.45 W (1.234 A)"
            if message.startswith("power:"):
                power_part = message.split("power:")[1].strip()

                # Extract watts - look for number before 'W'
                watts_match = re.search(r"([\d.]+)\s*W", power_part)
                if watts_match:
                    power_watts = float(watts_match.group(1))

                    # Apply noise threshold here as well
                    if (
                        power_watts < 5.0
                    ):  # Lower threshold - hair dryer should be 300-600W
                        power_watts = 0.0

                    print(f"[UDP] Parsed power: {power_watts:.2f}W")
                    return power_watts

                # Fallback: try to extract the first number
                numbers = re.findall(r"[\d.]+", power_part)
                if numbers:
                    power_watts = float(numbers[0])
                    if power_watts < 0.6:
                        power_watts = 0.0
                    return power_watts

            # Format 2: Direct number (legacy)
            elif message.replace(".", "").isdigit():
                power_watts = float(message)
                if power_watts < 5.0:
                    power_watts = 0.0
                return power_watts

            # Format 3: "POWER=123.45W"
            elif "POWER=" in message:
                power_match = re.search(r"POWER=([\d.]+)", message)
                if power_match:
                    power_watts = float(power_match.group(1))
                    if power_watts < 0.6:
                        power_watts = 0.0
                    return power_watts

            return None

        except (ValueError, IndexError) as e:
            print(f"[UDP] Failed to parse power message '{message}': {e}")
            return None

    def _send_discovery(self):
        """Send discovery broadcast"""
        try:
            discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            discovery_sock.sendto(b"DASHBOARD_READY", ("<broadcast>", 3334))
            discovery_sock.close()
            print("[UDP] Discovery broadcast sent")
        except Exception as e:
            print(f"[UDP] Discovery broadcast failed: {e}")
            # Try direct IP instead of broadcast
            try:
                discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Send to common ESP32 IP ranges
                for ip in ["192.168.1.161", "192.168.4.1", "192.168.0.161"]:
                    try:
                        discovery_sock.sendto(b"DASHBOARD_READY", (ip, 3334))
                    except:
                        pass
                discovery_sock.close()
                print("[UDP] Discovery sent to common IPs")
            except Exception as e2:
                print(f"[UDP] Discovery fallback also failed: {e2}")
