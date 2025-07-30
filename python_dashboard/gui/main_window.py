import threading
import tkinter as tk
from tkinter import messagebox, ttk

import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from utils.graph import animate_graph

from .calibration_window import CalibrationWindow
from .wifi_setup import WiFiSetupWindow


class MainWindow:
    """Main application window with auto-calibration support"""

    def __init__(self, parent, app, timestamps, power_values):
        self.parent = parent
        self.app = app
        self.timestamps = timestamps
        self.power_values = power_values

        self.setup_window()
        self.create_widgets()
        self.setup_graph()
        self.start_updates()

    def setup_window(self):
        """Configure the main window"""
        self.parent.title("ESP32 Smart Plug Dashboard - SCT-013-000 Auto-Calibration")
        self.parent.geometry("1200x900")

        # Create data directory
        import os

        os.makedirs("data", exist_ok=True)

    def create_widgets(self):
        """Create all GUI widgets"""
        self.create_status_bar()
        self.create_power_display()
        self.create_auto_cal_display()
        self.create_control_buttons()
        self.create_statistics_display()

    def create_status_bar(self):
        """Create status bar at top"""
        status_frame = ttk.Frame(self.parent)
        status_frame.pack(fill=tk.X, padx=15, pady=8)

        self.status_label = ttk.Label(
            status_frame,
            text="Status: Initializing...",
            foreground="blue",
            font=("", 10),
        )
        self.status_label.pack(side=tk.LEFT)

        self.info_label = ttk.Label(
            status_frame, text="ESP32: Not connected", foreground="gray", font=("", 9)
        )
        self.info_label.pack(side=tk.RIGHT)

    def create_power_display(self):
        """Create current power reading display"""
        power_frame = ttk.LabelFrame(self.parent, text="Current Reading", padding=10)
        power_frame.pack(pady=15, padx=15, fill=tk.X)

        power_display_frame = ttk.Frame(power_frame)
        power_display_frame.pack()

        ttk.Label(power_display_frame, text="Power:", font=("", 14)).pack(
            side=tk.LEFT, padx=5
        )
        self.current_label = ttk.Label(
            power_display_frame, text="--- W", font=("", 20, "bold"), foreground="green"
        )
        self.current_label.pack(side=tk.LEFT, padx=10)

        # Add current reading in amps
        ttk.Label(power_display_frame, text="Current:", font=("", 12)).pack(
            side=tk.LEFT, padx=(20, 5)
        )
        self.current_amps_label = ttk.Label(
            power_display_frame, text="--- A", font=("", 14, "bold"), foreground="blue"
        )
        self.current_amps_label.pack(side=tk.LEFT, padx=5)

    def create_auto_cal_display(self):
        """Create auto-calibration status display"""
        auto_cal_frame = ttk.LabelFrame(
            self.parent, text="Auto-Calibration Status", padding=10
        )
        auto_cal_frame.pack(pady=10, padx=15, fill=tk.X)

        # Auto-calibration status
        self.auto_cal_status_label = ttk.Label(
            auto_cal_frame, text="Auto-Cal: Initializing...", font=("", 10)
        )
        self.auto_cal_status_label.pack(side=tk.LEFT)

        # Auto-calibration controls
        control_frame = ttk.Frame(auto_cal_frame)
        control_frame.pack(side=tk.RIGHT)

        self.auto_cal_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            control_frame,
            text="Enable Auto-Calibration",
            variable=self.auto_cal_enabled_var,
            command=self.toggle_auto_calibration,
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            control_frame, text="Manual Trigger", command=self.trigger_auto_calibration
        ).pack(side=tk.LEFT, padx=5)

    def create_control_buttons(self):
        """Create control button panel"""
        btn_frame = ttk.LabelFrame(self.parent, text="Controls", padding=15)
        btn_frame.pack(pady=10, padx=15, fill=tk.X)

        # Row 1: Main controls
        row1_frame = ttk.Frame(btn_frame)
        row1_frame.pack(fill=tk.X, pady=8)

        ttk.Button(row1_frame, text="Toggle Relay", command=self.app.toggle_relay).pack(
            side=tk.LEFT, padx=8
        )

        ttk.Button(row1_frame, text="Save Data", command=self.app.save_data).pack(
            side=tk.LEFT, padx=8
        )

        ttk.Button(row1_frame, text="Clear Graph", command=self.app.clear_data).pack(
            side=tk.LEFT, padx=8
        )

        ttk.Button(row1_frame, text="WiFi Setup", command=self.open_wifi_setup).pack(
            side=tk.LEFT, padx=8
        )

        # Row 2: Calibration controls
        calib_frame = ttk.Frame(btn_frame)
        calib_frame.pack(fill=tk.X, pady=8)

        # Auto-detect button
        ttk.Button(
            calib_frame, text="Auto-Detect Load", command=self.auto_detect_load
        ).pack(side=tk.LEFT, padx=8)

        # SCT-013 info button
        ttk.Button(calib_frame, text="SCT Info", command=self.get_sct_info).pack(
            side=tk.LEFT, padx=8
        )

        # Quick bias fix button
        ttk.Button(calib_frame, text="Fix Bias", command=self.fix_bias_voltage).pack(
            side=tk.LEFT, padx=8
        )

        # Advanced calibration
        ttk.Button(
            calib_frame,
            text="Advanced Cal",
            command=self.open_calibration_window,
        ).pack(side=tk.LEFT, padx=8)

        # Row 3: Manual calibration and debug
        manual_frame = ttk.Frame(btn_frame)
        manual_frame.pack(fill=tk.X, pady=8)

        ttk.Label(manual_frame, text="Manual Cal (Amps):").pack(side=tk.LEFT, padx=5)
        self.calib_entry = ttk.Entry(manual_frame, width=12)
        self.calib_entry.pack(side=tk.LEFT, padx=8)
        self.calib_entry.insert(0, "5.0")

        ttk.Button(manual_frame, text="Calibrate", command=self.quick_calibrate).pack(
            side=tk.LEFT, padx=8
        )

        # Debug buttons
        ttk.Separator(manual_frame, orient=tk.VERTICAL).pack(
            side=tk.LEFT, padx=10, fill=tk.Y
        )

        ttk.Button(manual_frame, text="Debug ADC", command=self.debug_adc).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(manual_frame, text="Get Readings", command=self.get_readings).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(manual_frame, text="Status", command=self.get_status).pack(
            side=tk.LEFT, padx=5
        )

    def create_statistics_display(self):
        """Create statistics display"""
        stats_frame = ttk.LabelFrame(self.parent, text="Statistics & Info", padding=10)
        stats_frame.pack(pady=10, padx=15, fill=tk.X)

        self.stats_label = ttk.Label(
            stats_frame, text="Stats: Waiting for data...", font=("", 10)
        )
        self.stats_label.pack()

        # Add calibration info
        self.calib_info_label = ttk.Label(
            stats_frame,
            text="Calibration: SCT-013-000, 10 Ohm burden, 200 A/V theoretical",
            font=("", 9),
            foreground="gray",
        )
        self.calib_info_label.pack(pady=(5, 0))

    def setup_graph(self):
        """Setup the power usage graph"""
        graph_frame = ttk.LabelFrame(self.parent, text="Power Usage Graph", padding=10)
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        self.fig, self.ax = plt.subplots(figsize=(14, 7))
        self.fig.patch.set_facecolor("white")
        (self.line,) = self.ax.plot([], [])

        canvas = FigureCanvasTkAgg(self.fig, master=graph_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Start animation
        self.anim = animation.FuncAnimation(
            self.fig,
            self.animate_callback,
            interval=1000,
            cache_frame_data=False,
            blit=False,
        )

    def animate_callback(self, frame):
        """Animation callback for the graph"""
        try:
            result = animate_graph(
                frame,
                self.ax,
                self.line,
                self.current_label,
                self.stats_label,
                self.timestamps,
                self.power_values,
            )

            # Update current display
            if self.power_values:
                current_power = self.power_values[-1]
                current_amps = current_power / 120.0  # Assume 120V
                self.current_amps_label.config(text=f"{current_amps:.3f} A")

                # Color code the amperage
                if current_amps < 0.1:
                    color = "#888888"  # Gray for no load
                elif current_amps < 1.0:
                    color = "#27AE60"  # Green for light load
                elif current_amps < 3.0:
                    color = "#F39C12"  # Orange for medium load
                else:
                    color = "#E74C3C"  # Red for heavy load

                self.current_amps_label.config(foreground=color)

            return result
        except Exception as e:
            print(f"[GRAPH] Animation error: {e}")
            return (self.line,)

    def start_updates(self):
        """Start periodic updates"""
        self.update_connection_info()

    def update_connection_info(self, esp32_ip=None):
        """Update connection information display"""
        if esp32_ip:
            self.info_label.config(text=f"ESP32: {esp32_ip}", foreground="green")
        else:
            current_ip = self.app.get_current_esp32_ip()
            if current_ip:
                self.info_label.config(text=f"ESP32: {current_ip}", foreground="green")
            else:
                self.info_label.config(text="ESP32: Not connected", foreground="gray")

        # Schedule next update
        self.parent.after(2000, self.update_connection_info)

    def update_status(self, status, ip=None):
        """Update status label"""
        if ip:
            self.status_label.config(
                text=f"Status: Connected to {ip}", foreground="green"
            )
        else:
            self.status_label.config(text=f"Status: {status}", foreground="blue")

    def update_auto_cal_info(self, stats):
        """Update auto-calibration information display"""
        try:
            if isinstance(stats, dict):
                enabled = stats.get("ENABLED", False)
                count = stats.get("COUNT", 0)
                sensitivity = stats.get("SENSITIVITY", 0.0)
                learning_pts = stats.get("LEARNING_PTS", 0)

                status_text = f"Auto-Cal: {'ON' if enabled else 'OFF'}, Count: {count}, Learning: {learning_pts} pts, Sensitivity: {sensitivity:.2f}"
                self.auto_cal_status_label.config(text=status_text)
            else:
                self.auto_cal_status_label.config(text="Auto-Cal: Status unavailable")
        except Exception as e:
            print(f"[AUTO-CAL] Error updating display: {e}")

    def toggle_auto_calibration(self):
        """Toggle auto-calibration on/off"""
        enabled = self.auto_cal_enabled_var.get()
        result = self.app.toggle_auto_calibration(enabled)
        if result:
            status = "enabled" if enabled else "disabled"
            self.auto_cal_status_label.config(text=f"Auto-Cal: {status}")
        else:
            # Revert checkbox if command failed
            self.auto_cal_enabled_var.set(not enabled)

    def trigger_auto_calibration(self):
        """Manually trigger auto-calibration check"""
        result = self.app.trigger_auto_calibration_check()
        if result:
            messagebox.showinfo(
                "Auto-Calibration", "Manual auto-calibration check triggered"
            )
        else:
            messagebox.showerror("Error", "Failed to trigger auto-calibration")

    def auto_detect_load(self):
        """Auto-detect current load"""
        esp32_ip = self.app.get_current_esp32_ip()
        if not esp32_ip:
            messagebox.showerror("Error", "ESP32 not connected")
            return

        # Show progress dialog
        progress_window = tk.Toplevel(self.parent)
        progress_window.title("Auto-Detecting Load")
        progress_window.geometry("350x200")
        progress_window.grab_set()
        progress_window.transient(self.parent)

        ttk.Label(
            progress_window,
            text="Auto-detecting current load...",
            font=("", 12, "bold"),
        ).pack(pady=20)
        ttk.Label(
            progress_window,
            text="Make sure your device is ON and stable!",
            font=("", 10),
        ).pack(pady=5)

        progress_bar = ttk.Progressbar(progress_window, mode="indeterminate")
        progress_bar.pack(pady=20, padx=20, fill=tk.X)
        progress_bar.start()

        status_label = ttk.Label(progress_window, text="Analyzing signal...")
        status_label.pack()

        def detect():
            try:
                response = self.app.esp32_commands.auto_detect_load(esp32_ip)

                progress_bar.stop()
                progress_window.destroy()

                if response and "AUTO_DETECT_OK" in response:
                    detected_amps = float(response.split(":")[1])
                    power_watts = detected_amps * 120

                    classification = self.classify_load(detected_amps)

                    result_msg = (
                        f"Auto-Detection Results:\n\n"
                        f"Measurements:\n"
                        f"Current: {detected_amps:.2f} A\n"
                        f"Power: {power_watts:.0f} W (at 120V)\n\n"
                        f"Classification:\n{classification}\n\n"
                        f"Use '{detected_amps:.1f}' in manual calibration if needed."
                    )

                    messagebox.showinfo("Auto-Detection Results", result_msg)
                else:
                    messagebox.showerror("Error", "Auto-detection failed")

            except Exception as e:
                progress_bar.stop()
                if progress_window.winfo_exists():
                    progress_window.destroy()
                messagebox.showerror("Error", f"Detection failed: {e}")

        threading.Thread(target=detect, daemon=True).start()

    def classify_load(self, amps):
        """Classify the load based on current draw"""
        if amps < 0.1:
            return "No load or very light load\n(Standby devices, LEDs)"
        elif amps < 1.0:
            return "Light load\n(LED bulbs, phone chargers, small electronics)"
        elif amps < 3.0:
            return "Medium load\n(Incandescent bulbs, laptop chargers, small fans)"
        elif amps < 8.0:
            return "Heavy load\n(Hair dryers, space heaters, coffee makers)"
        elif amps < 15.0:
            return "Very heavy load\n(Microwaves, vacuum cleaners, power tools)"
        else:
            return "Extreme load\n(Industrial equipment, large appliances)"

    def fix_bias_voltage(self):
        """Quick bias voltage fix"""
        esp32_ip = self.app.get_current_esp32_ip()
        if not esp32_ip:
            messagebox.showerror("Error", "ESP32 not connected")
            return

        result = messagebox.askyesno(
            "Fix Bias Voltage",
            "This will recalibrate the bias voltage based on your current circuit.\n\n"
            "Make sure:\n"
            "- No devices are plugged into the extension cord\n"
            "- SCT-013 is properly connected\n"
            "- Circuit has been running for at least 30 seconds\n\n"
            "This should fix false high current readings.\n\n"
            "Continue?",
        )

        if result:
            try:
                response = self.app.recalibrate_bias()
                if response and "BIAS_RECALIBRATED" in response:
                    new_bias = response.split(":")[1] if ":" in response else "unknown"
                    messagebox.showinfo(
                        "Bias Fixed",
                        f"Bias voltage recalibrated!\n\n"
                        f"New bias voltage: {new_bias}V\n\n"
                        f"Current readings should now be accurate.\n"
                        f"Check the power display - it should show near 0W with no load.",
                    )
                else:
                    messagebox.showerror("Error", "Bias recalibration failed")
            except Exception as e:
                messagebox.showerror("Error", f"Bias recalibration failed: {e}")

    def debug_adc(self):
        """Debug ADC readings"""
        esp32_ip = self.app.get_current_esp32_ip()
        if not esp32_ip:
            messagebox.showerror("Error", "ESP32 not connected")
            return

        try:
            response = self.app.get_adc_debug()
            if response:
                messagebox.showinfo(
                    "ADC Debug",
                    f"Check serial monitor for detailed ADC readings.\n\nResponse: {response}",
                )
            else:
                messagebox.showerror("Error", "No response from ESP32")
        except Exception as e:
            messagebox.showerror("Error", f"ADC debug failed: {e}")

    def get_readings(self):
        """Get current sensor readings"""
        esp32_ip = self.app.get_current_esp32_ip()
        if not esp32_ip:
            messagebox.showerror("Error", "ESP32 not connected")
            return

        try:
            response = self.app.get_current_readings()
            if response and "CURRENT:" in response:
                # Parse the response for display
                parts = response.replace("CURRENT:", "").split(",")
                info_text = "Current Sensor Readings:\n\n"
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        info_text += f"{key}: {value}\n"

                messagebox.showinfo("Sensor Readings", info_text)
            else:
                messagebox.showerror("Error", "Invalid response from ESP32")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get readings: {e}")

    def get_status(self):
        """Get comprehensive status"""
        esp32_ip = self.app.get_current_esp32_ip()
        if not esp32_ip:
            messagebox.showerror("Error", "ESP32 not connected")
            return

        try:
            # Get multiple status types
            cal_status = self.app.get_calibration_status()
            auto_cal_stats = self.app.get_auto_cal_statistics()
            system_status = self.app.get_system_status()

            status_text = "ESP32 System Status:\n\n"

            if cal_status:
                status_text += f"Calibration: {cal_status}\n\n"

            if auto_cal_stats:
                status_text += f"Auto-Calibration: {auto_cal_stats}\n\n"

            if system_status:
                status_text += f"System: {system_status}\n"

            messagebox.showinfo("System Status", status_text)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get status: {e}")

    def get_sct_info(self):
        """Get SCT-013-000 sensor information"""
        esp32_ip = self.app.get_current_esp32_ip()
        if not esp32_ip:
            messagebox.showerror("Error", "ESP32 not connected")
            return

        try:
            response = self.app.esp32_commands.get_sct_info(esp32_ip)

            # Show comprehensive sensor information
            info_msg = (
                "SCT-013-000 Current Transformer\n\n"
                "Technical Specifications:\n"
                "- Model: SCT-013-000\n"
                "- Primary Current: 0-100A AC\n"
                "- Secondary Current: 0-50mA AC\n"
                "- Transformation Ratio: 2000:1\n"
                "- Accuracy: +/-1% (at rated current)\n"
                "- Frequency: 50/60Hz\n\n"
                "Your Configuration:\n"
                "- Burden Resistor: 10 Ohm\n"
                "- Output Voltage: 0-0.5V AC RMS\n"
                "- Sensitivity: ~5mV per amp\n"
                "- Linearity: Very good (0.1-100A)\n\n"
                "Calibration Information:\n"
                "- Theoretical Scale: 200 A/V\n"
                "- Zero Point: ~1.53V (your circuit)\n"
                "- Recommended Load: >0.5A for accuracy\n\n"
            )

            if response:
                info_msg += f"ESP32 Response: {response}\n\n"

            info_msg += (
                "Usage Tips:\n"
                "- Clamp around single wire only\n"
                "- Ensure proper orientation\n"
                "- Keep away from magnetic fields\n"
                "- Use steady loads for calibration\n"
                "- 10 Ohm burden gives better sensitivity than 33 Ohm"
            )

            messagebox.showinfo("SCT-013-000 Sensor Information", info_msg)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get sensor info: {e}")

    def quick_calibrate(self):
        """Quick calibration using the entry field"""
        value = self.calib_entry.get().strip()
        if value:
            try:
                amps = float(value)
                if 0.1 <= amps <= 20:
                    response = self.app.send_calibration(value)
                    if response and "CAL_KNOWN_OK" in response:
                        messagebox.showinfo(
                            "Success",
                            f"Manual Calibration Complete\n\n"
                            f"Calibrated with {amps}A load\n"
                            f"Power readings should now be accurate for this current level.",
                        )
                    else:
                        messagebox.showerror("Error", "Calibration command failed")
                else:
                    messagebox.showerror(
                        "Error", "Current must be between 0.1 and 20 amps"
                    )
            except ValueError:
                messagebox.showerror("Error", "Invalid number format")
        else:
            messagebox.showerror("Error", "Please enter a current value")

    def open_wifi_setup(self):
        """Open WiFi setup window"""
        WiFiSetupWindow(self.parent, self.app.send_wifi_credentials)

    def open_calibration_window(self):
        """Open advanced calibration window"""
        CalibrationWindow(self.parent, self.app)
