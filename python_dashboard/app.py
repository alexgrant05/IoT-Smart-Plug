import os
import sys
import threading
import tkinter as tk
from collections import deque

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modular components
from gui.main_window import MainWindow
from network.esp32_commands import ESP32Commands
from network.udp_handler import UDPHandler
from utils.data_manager import DataManager

# Global configuration
UDP_PORT_LISTEN = 3333
MAX_POINTS = 300  # Increased for longer history with auto-calibration


class SmartPlugApp:
    """Main application class with auto-calibration support"""

    def __init__(self):
        self.app_running = True

        # Thread-safe data storage
        self._data_lock = threading.Lock()
        self.timestamps = deque(maxlen=MAX_POINTS)
        self.power_values = deque(maxlen=MAX_POINTS)
        self.esp32_ip = None

        # Auto-calibration tracking
        self.auto_cal_events = deque(maxlen=50)  # Track auto-calibration events
        self.device_recognitions = deque(maxlen=30)  # Track device recognitions
        self.last_auto_cal_stats = {}

        # Initialize components
        self.data_manager = DataManager()
        self.esp32_commands = ESP32Commands()
        self.udp_handler = UDPHandler(
            port=UDP_PORT_LISTEN,
            data_callback=self.on_data_received,
            connection_callback=self.on_connection_status_changed,
        )

        # GUI components
        self.root = None
        self.main_window = None

    def on_data_received(self, power_value, source_ip):
        """Enhanced callback for data with auto-calibration awareness"""
        import time

        # Apply noise threshold - much lower for auto-calibration sensitivity
        if power_value < 1.0:  # Very low threshold to detect small changes
            power_value = 0.0

        with self._data_lock:
            self.timestamps.append(time.time())
            self.power_values.append(power_value)
            self.esp32_ip = source_ip

        # Update main window if available
        if self.main_window:
            self.root.after(0, self.main_window.update_connection_info, source_ip)

            # Check for auto-calibration events
            self.root.after(0, self.check_auto_calibration_status)

    def on_connection_status_changed(self, status, ip=None):
        """Callback when connection status changes"""
        if self.main_window:
            self.root.after(0, self.main_window.update_status, status, ip)

    def check_auto_calibration_status(self):
        """Periodically check auto-calibration status and update GUI"""
        try:
            ip = self.get_current_esp32_ip()
            if ip:
                # Get auto-calibration statistics
                response = self.esp32_commands.get_auto_cal_statistics(ip)
                if response and "AUTO_CAL_STATS:" in response:
                    stats_str = response.split("AUTO_CAL_STATS:")[1]
                    stats = self.parse_auto_cal_stats(stats_str)

                    # Check if auto-calibration count increased
                    if "COUNT" in stats and "COUNT" in self.last_auto_cal_stats:
                        if stats["COUNT"] > self.last_auto_cal_stats["COUNT"]:
                            # New auto-calibration event occurred
                            self.log_auto_cal_event("Auto-calibration performed", stats)

                    self.last_auto_cal_stats = stats

                    # Update main window with auto-cal info
                    if self.main_window:
                        self.main_window.update_auto_cal_info(stats)

        except Exception as e:
            print(f"[AUTO-CAL] Error checking status: {e}")

    def parse_auto_cal_stats(self, stats_str):
        """Parse auto-calibration statistics string"""
        stats = {}
        try:
            pairs = stats_str.split(",")
            for pair in pairs:
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    # Try to convert to appropriate type
                    try:
                        if value.isdigit():
                            stats[key] = int(value)
                        elif value.replace(".", "").isdigit():
                            stats[key] = float(value)
                        elif value.upper() in ["YES", "ON", "TRUE"]:
                            stats[key] = True
                        elif value.upper() in ["NO", "OFF", "FALSE"]:
                            stats[key] = False
                        else:
                            stats[key] = value
                    except:
                        stats[key] = value
        except Exception as e:
            print(f"[AUTO-CAL] Error parsing stats: {e}")
        return stats

    def log_auto_cal_event(self, event_type, stats=None):
        """Log auto-calibration events for user visibility"""
        import time

        event = {"timestamp": time.time(), "type": event_type, "stats": stats or {}}

        with self._data_lock:
            self.auto_cal_events.append(event)

        print(f"[AUTO-CAL] {event_type}: {stats}")

    def get_current_esp32_ip(self):
        """Get the current ESP32 IP for commands"""
        with self._data_lock:
            return self.esp32_ip

    def clear_data(self):
        """Clear all collected data"""
        with self._data_lock:
            count = len(self.power_values)
            self.timestamps.clear()
            self.power_values.clear()
            self.auto_cal_events.clear()
            self.device_recognitions.clear()
        print(f"Cleared {count} data points and auto-calibration history")
        return True

    def save_data(self):
        """Save current data to CSV with auto-calibration info"""
        with self._data_lock:
            timestamps_copy = list(self.timestamps)
            power_values_copy = list(self.power_values)
            auto_cal_events_copy = list(self.auto_cal_events)

        # Save power data
        success = self.data_manager.save_csv(timestamps_copy, power_values_copy)

        # Save auto-calibration events
        if success and auto_cal_events_copy:
            self.data_manager.save_auto_cal_events(auto_cal_events_copy)

        if success:
            print(
                f"Data saved successfully! {len(power_values_copy)} data points, {len(auto_cal_events_copy)} auto-cal events"
            )
        else:
            print("Failed to save data")
        return success

    # Enhanced ESP32 command wrappers with auto-calibration support
    def toggle_relay(self):
        """Toggle the ESP32 relay"""
        return self.esp32_commands.toggle_relay(self.get_current_esp32_ip())

    def send_calibration(self, value_str):
        """Send calibration command and log event"""
        result = self.esp32_commands.send_calibration(
            value_str, self.get_current_esp32_ip()
        )
        if result:
            self.log_auto_cal_event(f"Manual calibration: {value_str}A")
        return result

    def toggle_auto_calibration(self, enabled):
        """Toggle auto-calibration mode"""
        ip = self.get_current_esp32_ip()
        if enabled:
            result = self.esp32_commands.enable_auto_calibration(ip)
        else:
            result = self.esp32_commands.disable_auto_calibration(ip)

        if result:
            self.log_auto_cal_event(
                f"Auto-calibration {'enabled' if enabled else 'disabled'}"
            )
        return result

    def set_auto_cal_sensitivity(self, sensitivity):
        """Set auto-calibration sensitivity (0.0 to 1.0)"""
        return self.esp32_commands.set_auto_cal_sensitivity(
            sensitivity, self.get_current_esp32_ip()
        )

    def set_learning_rate(self, rate):
        """Set learning system rate (0.0 to 1.0)"""
        return self.esp32_commands.set_learning_rate(rate, self.get_current_esp32_ip())

    def get_auto_cal_statistics(self):
        """Get comprehensive auto-calibration statistics"""
        return self.esp32_commands.get_auto_cal_statistics(self.get_current_esp32_ip())

    def get_learning_statistics(self):
        """Get learning system statistics"""
        return self.esp32_commands.get_learning_statistics(self.get_current_esp32_ip())

    def reset_learning_data(self):
        """Reset learning system data"""
        result = self.esp32_commands.reset_learning_data(self.get_current_esp32_ip())
        if result:
            self.log_auto_cal_event("Learning data reset")
        return result

    def apply_learned_calibration(self):
        """Apply learned calibration immediately"""
        result = self.esp32_commands.apply_learned_calibration(
            self.get_current_esp32_ip()
        )
        if result:
            self.log_auto_cal_event("Applied learned calibration")
        return result

    def list_known_devices(self):
        """Get list of known devices for recognition"""
        return self.esp32_commands.list_known_devices(self.get_current_esp32_ip())

    def recognize_current_device(self, current_amps):
        """Try to recognize device from current consumption"""
        result = self.esp32_commands.recognize_device(
            current_amps, self.get_current_esp32_ip()
        )
        if result and "DEVICE_RECOGNIZED:" in result:
            device_info = result.split("DEVICE_RECOGNIZED:")[1]
            self.log_device_recognition(current_amps, device_info)
        return result

    def log_device_recognition(self, current_amps, device_info):
        """Log device recognition events"""
        import time

        recognition = {
            "timestamp": time.time(),
            "current": current_amps,
            "device_info": device_info,
        }

        with self._data_lock:
            self.device_recognitions.append(recognition)

        print(f"[DEVICE] Recognized: {current_amps:.2f}A -> {device_info}")

    def trigger_auto_calibration_check(self):
        """Manually trigger auto-calibration check"""
        result = self.esp32_commands.trigger_auto_calibration_check(
            self.get_current_esp32_ip()
        )
        if result:
            self.log_auto_cal_event("Manual auto-calibration check triggered")
        return result

    # Existing methods with auto-calibration awareness
    def recalibrate_bias(self):
        """Recalibrate bias voltage"""
        result = self.esp32_commands.zero_calibration(self.get_current_esp32_ip())
        if result:
            self.log_auto_cal_event("Bias voltage recalibrated")
        return result

    def get_adc_debug(self):
        """Get ADC debug information"""
        return self.esp32_commands.debug_adc(self.get_current_esp32_ip())

    def get_current_readings(self):
        """Get current sensor readings"""
        return self.esp32_commands.get_readings(self.get_current_esp32_ip())

    def get_calibration_status(self):
        """Request calibration status"""
        return self.esp32_commands.get_calibration_status(self.get_current_esp32_ip())

    def send_wifi_credentials(self, ssid, password):
        """Send WiFi credentials to ESP32"""
        return self.esp32_commands.send_wifi_credentials(ssid, password)

    def zero_calibration(self):
        """Perform zero point calibration"""
        result = self.esp32_commands.zero_calibration(self.get_current_esp32_ip())
        if result:
            self.log_auto_cal_event("Zero point calibration performed")
        return result

    def manual_calibration(self, bias_voltage, scale_factor):
        """Set manual calibration parameters"""
        result = self.esp32_commands.manual_calibration(
            bias_voltage, scale_factor, self.get_current_esp32_ip()
        )
        if result:
            self.log_auto_cal_event(
                f"Manual calibration: bias={bias_voltage:.4f}V, scale={scale_factor:.2f}A/V"
            )
        return result

    def reset_calibration(self):
        """Reset calibration to defaults"""
        result = self.esp32_commands.reset_calibration(self.get_current_esp32_ip())
        if result:
            self.log_auto_cal_event("Calibration reset to defaults")
        return result

    def get_system_status(self):
        """Get comprehensive system status"""
        return self.esp32_commands.get_system_status(self.get_current_esp32_ip())

    def get_measurement_statistics(self):
        """Get measurement statistics from ESP32"""
        return self.esp32_commands.get_measurement_statistics(
            self.get_current_esp32_ip()
        )

    def reset_statistics(self):
        """Reset all statistics on ESP32"""
        result = self.esp32_commands.reset_statistics(self.get_current_esp32_ip())
        if result:
            self.log_auto_cal_event("Statistics reset")
        return result

    def get_auto_cal_events(self):
        """Get auto-calibration events for display"""
        with self._data_lock:
            return list(self.auto_cal_events)

    def get_device_recognitions(self):
        """Get device recognition events for display"""
        with self._data_lock:
            return list(self.device_recognitions)

    def run(self):
        """Start the application with auto-calibration support"""
        print("Starting ESP32 Smart Plug Dashboard with Auto-Calibration...")
        print("Features: Auto-Calibration, Device Recognition, Learning System")
        print("SCT-013-000 with 10Ω burden resistor configuration")

        # Create main window
        self.root = tk.Tk()
        self.main_window = MainWindow(
            parent=self.root,
            app=self,  # Pass reference to this app
            timestamps=self.timestamps,
            power_values=self.power_values,
        )

        # Start UDP listener
        self.udp_handler.start()

        # Start periodic auto-calibration status checking
        self.start_auto_cal_monitoring()

        # Setup cleanup
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Start GUI
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.on_closing()

    def start_auto_cal_monitoring(self):
        """Start periodic monitoring of auto-calibration system"""

        def monitor():
            if self.app_running:
                self.check_auto_calibration_status()
                # Schedule next check in 30 seconds
                self.root.after(30000, monitor)

        # Start monitoring after 5 seconds
        self.root.after(5000, monitor)

    def on_closing(self):
        """Clean shutdown"""
        print("[APP] Shutting down auto-calibration aware dashboard...")
        self.app_running = False

        if self.udp_handler:
            self.udp_handler.stop()

        if self.root:
            self.root.destroy()


def main():
    """Application entry point"""
    try:
        app = SmartPlugApp()
        app.run()
    except Exception as e:
        print(f"Application error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
