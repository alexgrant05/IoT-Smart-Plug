import tkinter as tk
from tkinter import messagebox, ttk


class CalibrationWindow:
    """Advanced calibration window with multiple calibration methods"""

    def __init__(self, parent, app):
        self.parent = parent
        self.app = app

        self.window = tk.Toplevel(parent)
        self.window.title("Advanced Calibration - SCT-013-000")
        self.window.geometry("700x650")
        self.window.grab_set()

        self.create_widgets()

    def create_widgets(self):
        """Create all calibration widgets"""
        # Main notebook for different calibration methods
        notebook = ttk.Notebook(self.window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Method 1: Known Device Calibration
        self.create_known_device_tab(notebook)

        # Method 2: Two-Point Calibration
        self.create_two_point_tab(notebook)

        # Method 3: Manual Calibration
        self.create_manual_tab(notebook)

        # Method 4: Circuit-Specific Calibration
        self.create_circuit_specific_tab(notebook)

        # Status and control buttons
        self.create_control_section()

    def create_known_device_tab(self, notebook):
        """Calibration using a device with known power consumption"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Known Device")

        # Instructions
        instructions = tk.Text(frame, height=6, wrap=tk.WORD)
        instructions.pack(fill=tk.X, padx=10, pady=10)
        instructions.insert(
            tk.END,
            "Known Device Calibration Method:\n\n"
            "1. Connect a device with known power consumption (e.g., 60W light bulb)\n"
            "2. Turn on the device and wait for stable readings\n"
            "3. Enter the known current draw below\n"
            "4. Click 'Calibrate with Known Current'\n\n"
            "This method works best with purely resistive loads like incandescent bulbs.",
        )
        instructions.config(state=tk.DISABLED)

        # Input section
        input_frame = ttk.LabelFrame(frame, text="Device Information", padding=10)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(input_frame, text="Known Current (Amps):").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.known_current_entry = ttk.Entry(input_frame, width=15)
        self.known_current_entry.grid(row=0, column=1, padx=5, pady=5)
        self.known_current_entry.insert(0, "0.5")

        ttk.Label(input_frame, text="Device Type:").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.device_type = ttk.Combobox(
            input_frame,
            values=[
                "Incandescent Bulb (Resistive)",
                "LED Bulb (Switching)",
                "Heater (Resistive)",
                "Motor (Inductive)",
                "Other",
            ],
        )
        self.device_type.grid(row=1, column=1, padx=5, pady=5)
        self.device_type.set("Incandescent Bulb (Resistive)")

        ttk.Button(
            input_frame,
            text="Calibrate with Known Current",
            command=self.calibrate_known_device,
        ).grid(row=2, column=0, columnspan=2, pady=10)

    def create_two_point_tab(self, notebook):
        """Two-point calibration for better linearity"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Two-Point")

        # Instructions
        instructions = tk.Text(frame, height=6, wrap=tk.WORD)
        instructions.pack(fill=tk.X, padx=10, pady=10)
        instructions.insert(
            tk.END,
            "Two-Point Calibration Method:\n\n"
            "1. First, calibrate with no load (zero point)\n"
            "2. Then calibrate with a known load (scale point)\n"
            "3. This creates a linear calibration curve for better accuracy\n"
            "4. Recommended for the most accurate readings across all power levels\n\n"
            "This method provides the best overall accuracy for your SCT-013-000.",
        )
        instructions.config(state=tk.DISABLED)

        # Two-point calibration controls
        calib_frame = ttk.LabelFrame(frame, text="Two-Point Calibration", padding=10)
        calib_frame.pack(fill=tk.X, padx=10, pady=10)

        # Step 1: Zero point
        ttk.Label(
            calib_frame, text="Step 1: Zero Point Calibration", font=("", 10, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Label(calib_frame, text="Ensure no load is connected").grid(
            row=1, column=0, sticky=tk.W, padx=20
        )
        ttk.Button(
            calib_frame,
            text="Calibrate Zero Point",
            command=self.calibrate_zero_point,
        ).grid(row=1, column=1, padx=5)

        # Step 2: Scale point
        ttk.Label(
            calib_frame, text="Step 2: Scale Point Calibration", font=("", 10, "bold")
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(15, 5))
        ttk.Label(calib_frame, text="Known load current (A):").grid(
            row=3, column=0, sticky=tk.W, padx=20
        )
        self.scale_current_entry = ttk.Entry(calib_frame, width=15)
        self.scale_current_entry.grid(row=3, column=1, padx=5)
        self.scale_current_entry.insert(0, "0.5")

        ttk.Button(
            calib_frame,
            text="Calibrate Scale Point",
            command=self.calibrate_scale_point,
        ).grid(row=4, column=0, columnspan=2, pady=10)

        # Status
        self.two_point_status = ttk.Label(
            calib_frame, text="Status: Ready for zero point calibration"
        )
        self.two_point_status.grid(row=5, column=0, columnspan=2, pady=5)

    def create_manual_tab(self, notebook):
        """Manual calibration parameters"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Manual")

        # Instructions
        instructions = tk.Text(frame, height=6, wrap=tk.WORD)
        instructions.pack(fill=tk.X, padx=10, pady=10)
        instructions.insert(
            tk.END,
            "Manual Calibration Method:\n\n"
            "1. Bias Voltage: The DC voltage level with no AC signal (your circuit: ~1.533V)\n"
            "2. Scale Factor: Converts RMS voltage to current (theoretical: 200 A/V)\n"
            "3. Use this when you know the exact parameters for your circuit\n"
            "4. Advanced users can fine-tune both parameters independently\n\n"
            "Your SCT-013-000 with 10Ω burden resistor has specific optimal values.",
        )
        instructions.config(state=tk.DISABLED)

        # Manual calibration controls
        manual_frame = ttk.LabelFrame(
            frame, text="Manual Calibration Parameters", padding=10
        )
        manual_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(manual_frame, text="Bias Voltage (V):").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.bias_voltage_entry = ttk.Entry(manual_frame, width=15)
        self.bias_voltage_entry.grid(row=0, column=1, padx=5, pady=5)
        self.bias_voltage_entry.insert(0, "1.533")

        ttk.Label(manual_frame, text="Scale Factor (A/V):").grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.scale_factor_entry = ttk.Entry(manual_frame, width=15)
        self.scale_factor_entry.grid(row=1, column=1, padx=5, pady=5)
        self.scale_factor_entry.insert(0, "200.0")

        ttk.Button(
            manual_frame,
            text="Set Manual Calibration",
            command=self.set_manual_calibration,
        ).grid(row=2, column=0, columnspan=2, pady=10)

    def create_circuit_specific_tab(self, notebook):
        """Circuit-specific calibration and diagnostics"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Circuit Debug")

        # Instructions
        instructions = tk.Text(frame, height=4, wrap=tk.WORD)
        instructions.pack(fill=tk.X, padx=10, pady=10)
        instructions.insert(
            tk.END,
            "Circuit-Specific Calibration:\n\n"
            "Your circuit uses a 10Ω burden resistor with voltage divider biasing.\n"
            "Use these tools to diagnose and fix calibration issues specific to your setup.",
        )
        instructions.config(state=tk.DISABLED)

        # Current readings section
        readings_frame = ttk.LabelFrame(
            frame, text="Real-Time Sensor Readings", padding=10
        )
        readings_frame.pack(fill=tk.X, padx=10, pady=10)

        self.raw_reading_label = ttk.Label(readings_frame, text="Raw ADC: ---")
        self.raw_reading_label.pack(anchor=tk.W)

        self.voltage_reading_label = ttk.Label(readings_frame, text="Voltage: --- V")
        self.voltage_reading_label.pack(anchor=tk.W)

        self.bias_reading_label = ttk.Label(readings_frame, text="Bias: --- V")
        self.bias_reading_label.pack(anchor=tk.W)

        self.current_reading_label = ttk.Label(readings_frame, text="Current: --- A")
        self.current_reading_label.pack(anchor=tk.W)

        # Control buttons
        btn_frame = ttk.Frame(readings_frame)
        btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            btn_frame, text="Refresh Readings", command=self.refresh_readings
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Debug ADC", command=self.debug_adc).pack(
            side=tk.LEFT, padx=5
        )

        ttk.Button(btn_frame, text="Fix Bias Now", command=self.fix_bias_voltage).pack(
            side=tk.LEFT, padx=5
        )

    def create_control_section(self):
        """Create control buttons and status"""
        control_frame = ttk.Frame(self.window)
        control_frame.pack(fill=tk.X, padx=15, pady=10)

        # Status display
        self.status_label = ttk.Label(
            control_frame,
            text="Status: Ready for calibration",
            font=("", 10),
            foreground="blue",
        )
        self.status_label.pack(side=tk.LEFT)

        # Control buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(side=tk.RIGHT)

        ttk.Button(
            btn_frame, text="Get Status", command=self.get_calibration_status
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            btn_frame, text="Reset to Defaults", command=self.reset_calibration
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Close", command=self.window.destroy).pack(
            side=tk.LEFT, padx=5
        )

    def calibrate_known_device(self):
        """Calibrate using a device with known current consumption"""
        try:
            current = float(self.known_current_entry.get())

            if current <= 0 or current > 20:
                messagebox.showerror("Error", "Current must be between 0.1 and 20 amps")
                return

            response = self.app.send_calibration(str(current))
            if response and "CAL_KNOWN_OK" in response:
                self.status_label.config(
                    text=f"✓ Calibrated with {current:.3f}A device",
                    foreground="green",
                )
            else:
                self.status_label.config(
                    text="✗ Calibration failed - check ESP32 connection",
                    foreground="red",
                )
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid current value")

    def calibrate_zero_point(self):
        """Calibrate zero point (no load)"""
        response = messagebox.askyesno(
            "Zero Point Calibration",
            "Make sure NO devices are connected to the smart plug.\n\n"
            "The sensor will measure the zero-current baseline.\n\n"
            "Continue with zero point calibration?",
        )

        if response:
            result = self.app.zero_calibration()
            if result and "ZERO_CAL_OK" in str(result):
                self.two_point_status.config(
                    text="✓ Zero point calibrated. Ready for scale point."
                )
                self.status_label.config(
                    text="✓ Zero point calibration complete", foreground="green"
                )
            else:
                self.two_point_status.config(text="✗ Zero point calibration failed")
                self.status_label.config(
                    text="✗ Zero point calibration failed", foreground="red"
                )

    def calibrate_scale_point(self):
        """Calibrate scale point with known current"""
        try:
            current = float(self.scale_current_entry.get())

            response = messagebox.askyesno(
                "Scale Point Calibration",
                f"Connect a device that draws {current:.3f}A\n"
                f"(approximately {current * 120:.1f}W at 120V)\n\n"
                "Make sure the device is ON and drawing power.\n\n"
                "Continue with scale point calibration?",
            )

            if response:
                result = self.app.esp32_commands.scale_calibration(
                    current, self.app.get_current_esp32_ip()
                )
                if result and "SCALE_CAL_OK" in str(result):
                    self.two_point_status.config(
                        text="✓ Two-point calibration complete!"
                    )
                    self.status_label.config(
                        text="✓ Two-point calibration complete", foreground="green"
                    )
                else:
                    self.two_point_status.config(
                        text="✗ Scale point calibration failed"
                    )
                    self.status_label.config(
                        text="✗ Scale point calibration failed", foreground="red"
                    )
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid current value")

    def set_manual_calibration(self):
        """Set manual calibration parameters"""
        try:
            bias_voltage = float(self.bias_voltage_entry.get())
            scale_factor = float(self.scale_factor_entry.get())

            response = messagebox.askyesno(
                "Manual Calibration",
                f"Set calibration parameters:\n"
                f"Bias Voltage: {bias_voltage:.4f}V\n"
                f"Scale Factor: {scale_factor:.1f} A/V\n\n"
                "This will override current calibration.\n"
                "Continue?",
            )

            if response:
                result = self.app.manual_calibration(bias_voltage, scale_factor)
                if result and "MANUAL_CAL_OK" in str(result):
                    self.status_label.config(
                        text=f"✓ Manual calibration set: {bias_voltage:.4f}V, {scale_factor:.1f}A/V",
                        foreground="green",
                    )
                else:
                    self.status_label.config(
                        text="✗ Manual calibration failed", foreground="red"
                    )
        except ValueError:
            messagebox.showerror("Error", "Please enter valid calibration values")

    def refresh_readings(self):
        """Request current sensor readings from ESP32"""
        try:
            response = self.app.get_current_readings()
            if response and "READINGS:" in response:
                # Parse and display readings
                parts = response.replace("READINGS:", "").split(",")
                for part in parts:
                    if "RAW=" in part:
                        self.raw_reading_label.config(
                            text=f"Raw ADC: {part.split('=')[1]}"
                        )
                    elif "VOLT=" in part:
                        self.voltage_reading_label.config(
                            text=f"Voltage: {part.split('=')[1]}V"
                        )
                    elif "BIAS=" in part:
                        self.bias_reading_label.config(
                            text=f"Bias: {part.split('=')[1]}V"
                        )
                    elif "CURR=" in part:
                        self.current_reading_label.config(
                            text=f"Current: {part.split('=')[1]}A"
                        )

                self.status_label.config(text="✓ Readings updated", foreground="green")
            else:
                self.status_label.config(
                    text="✗ Failed to get readings", foreground="red"
                )
        except Exception as e:
            self.status_label.config(text=f"✗ Error: {e}", foreground="red")

    def debug_adc(self):
        """Debug ADC readings"""
        result = self.app.get_adc_debug()
        if result:
            self.status_label.config(
                text="✓ ADC debug sent - check serial monitor", foreground="blue"
            )
        else:
            self.status_label.config(text="✗ ADC debug failed", foreground="red")

    def fix_bias_voltage(self):
        """Quick bias voltage fix"""
        response = messagebox.askyesno(
            "Fix Bias Voltage",
            "This will recalibrate the bias voltage for your circuit.\n\n"
            "Make sure no devices are connected and the circuit is stable.\n\n"
            "Continue?",
        )

        if response:
            result = self.app.recalibrate_bias()
            if result and "BIAS_RECALIBRATED" in str(result):
                new_bias = (
                    str(result).split(":")[1] if ":" in str(result) else "unknown"
                )
                self.status_label.config(
                    text=f"✓ Bias recalibrated to {new_bias}V", foreground="green"
                )
                # Update the manual entry field
                self.bias_voltage_entry.delete(0, tk.END)
                self.bias_voltage_entry.insert(0, new_bias)
            else:
                self.status_label.config(
                    text="✗ Bias recalibration failed", foreground="red"
                )

    def get_calibration_status(self):
        """Get current calibration status"""
        result = self.app.get_calibration_status()
        if result:
            self.status_label.config(
                text="✓ Status retrieved - check console", foreground="blue"
            )
        else:
            self.status_label.config(text="✗ Failed to get status", foreground="red")

    def reset_calibration(self):
        """Reset calibration to factory defaults"""
        response = messagebox.askyesno(
            "Reset Calibration",
            "This will reset all calibration to SCT-013-000 defaults:\n"
            "- Bias Voltage: 1.65V\n"
            "- Scale Factor: 200.0 A/V\n\n"
            "Continue with reset?",
        )

        if response:
            result = self.app.reset_calibration()
            if result and "RESET_CAL_OK" in str(result):
                self.status_label.config(
                    text="✓ Calibration reset to defaults", foreground="green"
                )
                # Update entry fields to show defaults
                self.bias_voltage_entry.delete(0, tk.END)
                self.bias_voltage_entry.insert(0, "1.65")
                self.scale_factor_entry.delete(0, tk.END)
                self.scale_factor_entry.insert(0, "200.0")
            else:
                self.status_label.config(text="✗ Reset failed", foreground="red")
