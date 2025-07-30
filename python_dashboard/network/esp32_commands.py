import socket


class ESP32Commands:
    """Enhanced ESP32 command handler with auto-calibration support"""

    def __init__(self, timeout=5):
        self.timeout = timeout
        self.esp_setup_ip = "192.168.4.1"
        self.esp_setup_port = 4567
        self.esp_control_port = 3334

    def _send_command(self, command, esp32_ip, port=None, expect_response=True):
        """Send UDP command to ESP32"""
        if not esp32_ip:
            print("[CMD] No ESP32 IP available")
            return False

        if port is None:
            port = self.esp_control_port

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(self.timeout)
                s.sendto(command.encode(), (esp32_ip, port))
                print(f"[CMD] Sent '{command}' to {esp32_ip}:{port}")

                if expect_response:
                    try:
                        response, addr = s.recvfrom(1024)
                        response_str = response.decode().strip()
                        print(f"[CMD] Response: {response_str}")
                        return response_str
                    except socket.timeout:
                        print(f"[CMD] No response to '{command}'")
                        return None
                else:
                    return True

        except Exception as e:
            print(f"[CMD] Failed to send '{command}': {e}")
            return False

    # === BASIC COMMANDS ===
    def toggle_relay(self, esp32_ip):
        """Toggle the relay"""
        return self._send_command("RELAY_TOGGLE", esp32_ip)

    def ping_esp32(self, esp32_ip):
        """Ping ESP32 to check connectivity"""
        return self._send_command("PING", esp32_ip)

    # === AUTO-CALIBRATION COMMANDS ===
    def enable_auto_calibration(self, esp32_ip):
        """Enable auto-calibration"""
        return self._send_command("AUTO_CAL_ON", esp32_ip)

    def disable_auto_calibration(self, esp32_ip):
        """Disable auto-calibration"""
        return self._send_command("AUTO_CAL_OFF", esp32_ip)

    def get_auto_cal_statistics(self, esp32_ip):
        """Get auto-calibration statistics"""
        return self._send_command("AUTO_CAL_STATUS", esp32_ip)

    def set_auto_cal_sensitivity(self, sensitivity, esp32_ip):
        """Set auto-calibration sensitivity (0.0 to 1.0)"""
        if not (0.0 <= sensitivity <= 1.0):
            print(f"[CMD] Invalid sensitivity: {sensitivity} (must be 0.0-1.0)")
            return False
        return self._send_command(f"AUTO_CAL_SENSITIVITY:{sensitivity}", esp32_ip)

    def set_learning_rate(self, rate, esp32_ip):
        """Set learning system rate (0.0 to 1.0)"""
        if not (0.0 <= rate <= 1.0):
            print(f"[CMD] Invalid learning rate: {rate} (must be 0.0-1.0)")
            return False
        return self._send_command(f"AUTO_CAL_LEARNING_RATE:{rate}", esp32_ip)

    def trigger_auto_calibration_check(self, esp32_ip):
        """Manually trigger auto-calibration check"""
        return self._send_command("TRIGGER_AUTO_CAL", esp32_ip)

    # === DEVICE RECOGNITION ===
    def list_known_devices(self, esp32_ip):
        """Get list of known devices for recognition"""
        return self._send_command("LIST_DEVICES", esp32_ip)

    def recognize_device(self, current_amps, esp32_ip):
        """Try to recognize device from current consumption"""
        return self._send_command(f"RECOGNIZE_CURRENT:{current_amps}", esp32_ip)

    def auto_recognize_current_load(self, esp32_ip):
        """Auto-recognize current load and potentially calibrate"""
        return self._send_command("AUTO_RECOGNIZE", esp32_ip)

    # === LEARNING SYSTEM ===
    def get_learning_statistics(self, esp32_ip):
        """Get learning system statistics"""
        return self._send_command("LEARNING_STATS", esp32_ip)

    def reset_learning_data(self, esp32_ip):
        """Reset learning system data"""
        return self._send_command("RESET_LEARNING", esp32_ip)

    def apply_learned_calibration(self, esp32_ip):
        """Apply learned calibration immediately"""
        return self._send_command("APPLY_LEARNING", esp32_ip)

    # === CALIBRATION COMMANDS ===
    def send_calibration(self, value_str, esp32_ip):
        """Send calibration value (legacy command)"""
        try:
            value = float(value_str.strip())
            if value <= 0 or value > 100:
                print(f"[CMD] Invalid calibration value: {value}")
                return False
            return self._send_command(f"CAL_KNOWN:{value}", esp32_ip)
        except ValueError:
            print(f"[CMD] Invalid calibration format: {value_str}")
            return False

    def zero_calibration(self, esp32_ip):
        """Perform zero-point calibration"""
        return self._send_command("ZERO_CAL", esp32_ip)

    def scale_calibration(self, current_value, esp32_ip):
        """Perform scale calibration"""
        try:
            current = float(current_value)
            if current <= 0 or current > 100:
                print(f"[CMD] Invalid scale current: {current}")
                return False
            return self._send_command(f"SCALE_CAL:{current}", esp32_ip)
        except ValueError:
            print(f"[CMD] Invalid scale current format: {current_value}")
            return False

    def manual_calibration(self, bias_voltage, scale_factor, esp32_ip):
        """Set manual calibration parameters"""
        try:
            bias = float(bias_voltage)
            scale = float(scale_factor)
            return self._send_command(f"MANUAL_CAL:{bias},{scale}", esp32_ip)
        except ValueError:
            print("[CMD] Invalid manual calibration parameters")
            return False

    def reset_calibration(self, esp32_ip):
        """Reset calibration to defaults"""
        return self._send_command("RESET_CAL", esp32_ip)

    def get_calibration_status(self, esp32_ip):
        """Get calibration status"""
        return self._send_command("CAL_STATUS", esp32_ip)

    def recalibrate_bias(self, esp32_ip):
        """Recalibrate bias voltage (legacy command)"""
        return self._send_command("RECALIBRATE_BIAS", esp32_ip)

    # === MEASUREMENT AND DIAGNOSTICS ===
    def get_readings(self, esp32_ip):
        """Get current sensor readings"""
        return self._send_command("GET_CURRENT", esp32_ip)

    def debug_adc(self, esp32_ip):
        """Get ADC debug information"""
        return self._send_command("DEBUG_ADC", esp32_ip)

    def get_measurement_statistics(self, esp32_ip):
        """Get measurement statistics"""
        return self._send_command("MEASUREMENT_STATS", esp32_ip)

    def reset_statistics(self, esp32_ip):
        """Reset all statistics"""
        return self._send_command("RESET_STATS", esp32_ip)

    def analyze_voltage_buffer(self, esp32_ip):
        """Get voltage buffer analysis"""
        return self._send_command("BUFFER_ANALYSIS", esp32_ip)

    # === AUTO-DETECTION ===
    def auto_detect_load(self, esp32_ip):
        """Auto-detect current load"""
        return self._send_command("AUTO_DETECT", esp32_ip)

    def enable_auto_detection(self, esp32_ip):
        """Enable auto-detection"""
        return self._send_command("AUTO_DETECT_ON", esp32_ip)

    def disable_auto_detection(self, esp32_ip):
        """Disable auto-detection"""
        return self._send_command("AUTO_DETECT_OFF", esp32_ip)

    # === SYSTEM CONTROL ===
    def get_system_status(self, esp32_ip):
        """Get comprehensive system status"""
        return self._send_command("SYSTEM_STATUS", esp32_ip)

    def get_sct_info(self, esp32_ip):
        """Get SCT sensor information"""
        return self._send_command("SCT_INFO", esp32_ip)

    def restart_esp32(self, esp32_ip):
        """Restart the ESP32"""
        return self._send_command("RESTART", esp32_ip, expect_response=False)

    def get_configuration(self, esp32_ip):
        """Get ESP32 configuration"""
        return self._send_command("GET_CONFIG", esp32_ip)

    def get_help(self, esp32_ip):
        """Get available commands"""
        return self._send_command("HELP", esp32_ip)

    # === PARAMETER SETTING ===
    def set_bias_voltage(self, bias_voltage, esp32_ip):
        """Set bias voltage directly"""
        try:
            bias = float(bias_voltage)
            if not (0.1 <= bias <= 3.0):
                print(f"[CMD] Invalid bias voltage: {bias} (must be 0.1-3.0V)")
                return False
            return self._send_command(f"SET_BIAS:{bias}", esp32_ip)
        except ValueError:
            print(f"[CMD] Invalid bias voltage format: {bias_voltage}")
            return False

    def set_scale_factor(self, scale_factor, esp32_ip):
        """Set scale factor directly"""
        try:
            scale = float(scale_factor)
            if not (1.0 <= scale <= 1000.0):
                print(f"[CMD] Invalid scale factor: {scale} (must be 1.0-1000.0)")
                return False
            return self._send_command(f"SET_SCALE:{scale}", esp32_ip)
        except ValueError:
            print(f"[CMD] Invalid scale factor format: {scale_factor}")
            return False

    # === WIFI SETUP ===
    def send_wifi_credentials(self, ssid, password):
        """Send WiFi credentials to ESP32 in setup mode"""
        if not ssid:
            print("[CMD] SSID cannot be empty")
            return False

        if not password:
            password = ""

        message = f"{ssid},{password}"

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(10)
                s.sendto(message.encode(), (self.esp_setup_ip, self.esp_setup_port))
                print(f"[CMD] WiFi credentials sent to {self.esp_setup_ip}")
                return True
        except Exception as e:
            print(f"[CMD] Failed to send WiFi credentials: {e}")
            return False

    # === ADVANCED DIAGNOSTICS ===
    def comprehensive_diagnostic(self, esp32_ip):
        """Run comprehensive diagnostic and return results"""
        print("[CMD] Running comprehensive diagnostic...")

        results = {}

        # System status
        results["system_status"] = self.get_system_status(esp32_ip)

        # Calibration status
        results["calibration_status"] = self.get_calibration_status(esp32_ip)

        # Auto-calibration statistics
        results["auto_cal_stats"] = self.get_auto_cal_statistics(esp32_ip)

        # Learning statistics
        results["learning_stats"] = self.get_learning_statistics(esp32_ip)

        # Measurement statistics
        results["measurement_stats"] = self.get_measurement_statistics(esp32_ip)

        # Current readings
        results["current_readings"] = self.get_readings(esp32_ip)

        # Device list
        results["known_devices"] = self.list_known_devices(esp32_ip)

        # SCT sensor info
        results["sct_info"] = self.get_sct_info(esp32_ip)

        # Buffer analysis
        results["buffer_analysis"] = self.analyze_voltage_buffer(esp32_ip)

        print("[CMD] Comprehensive diagnostic complete")
        return results

    # === BULK CONFIGURATION ===
    def configure_auto_calibration(
        self, esp32_ip, enabled=True, sensitivity=0.7, learning_rate=0.1
    ):
        """Configure auto-calibration system in one command"""
        print(
            f"[CMD] Configuring auto-calibration: enabled={enabled}, sensitivity={sensitivity}, learning_rate={learning_rate}"
        )

        results = {}

        # Enable/disable auto-calibration
        if enabled:
            results["enable"] = self.enable_auto_calibration(esp32_ip)
        else:
            results["enable"] = self.disable_auto_calibration(esp32_ip)

        # Set sensitivity
        results["sensitivity"] = self.set_auto_cal_sensitivity(sensitivity, esp32_ip)

        # Set learning rate
        results["learning_rate"] = self.set_learning_rate(learning_rate, esp32_ip)

        # Get final status
        results["final_status"] = self.get_auto_cal_statistics(esp32_ip)

        return results

    def factory_reset_calibration(self, esp32_ip):
        """Perform complete factory reset of calibration system"""
        print("[CMD] Performing factory reset of calibration system...")

        results = {}

        # Reset calibration to defaults
        results["reset_cal"] = self.reset_calibration(esp32_ip)

        # Reset learning data
        results["reset_learning"] = self.reset_learning_data(esp32_ip)

        # Reset statistics
        results["reset_stats"] = self.reset_statistics(esp32_ip)

        # Enable auto-calibration with default settings
        results["enable_auto_cal"] = self.enable_auto_calibration(esp32_ip)

        # Set default sensitivity
        results["set_sensitivity"] = self.set_auto_cal_sensitivity(0.7, esp32_ip)

        # Set default learning rate
        results["set_learning_rate"] = self.set_learning_rate(0.1, esp32_ip)

        # Get final status
        results["final_status"] = self.get_system_status(esp32_ip)

        print("[CMD] Factory reset complete")
        return results
