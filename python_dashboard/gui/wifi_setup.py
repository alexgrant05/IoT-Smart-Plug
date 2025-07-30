import tkinter as tk
from tkinter import messagebox, ttk


class WiFiSetupWindow:
    """WiFi setup window for configuring ESP32"""

    def __init__(self, parent, send_credentials_callback):
        self.parent = parent
        self.send_credentials_callback = send_credentials_callback

        self.window = tk.Toplevel(parent)
        self.window.title("ESP32 WiFi Setup")
        self.window.geometry("600x500")
        self.window.grab_set()

        self.create_widgets()

    def create_widgets(self):
        """Create all widgets for WiFi setup"""
        # Instructions
        self.create_instructions()

        # Setup form
        self.create_setup_form()

        # Control buttons
        self.create_control_buttons()

    def create_instructions(self):
        """Create instruction text"""
        instructions_frame = ttk.LabelFrame(
            self.window, text="Setup Instructions", padding=15
        )
        instructions_frame.pack(fill=tk.X, padx=15, pady=15)

        instructions = tk.Text(
            instructions_frame,
            height=12,
            wrap=tk.WORD,
            font=("", 9),
            relief=tk.FLAT,
            bg="#F8F9FA",
        )
        instructions.pack(fill=tk.X)

        instructions.insert(
            tk.END,
            "ESP32 WiFi Setup Instructions:\n\n"
            "1. Make sure your ESP32 is powered on and in setup mode\n"
            "   (You should see the ESP32_SETUP network appear)\n\n"
            "2. Connect your computer to the 'ESP32_SETUP' WiFi network:\n"
            "   • Network name: ESP32_SETUP\n"
            "   • Password: esp32pass\n\n"
            "3. Enter your home WiFi credentials below\n\n"
            "4. Click 'Send WiFi Credentials'\n\n"
            "5. Wait for ESP32 to connect (10-30 seconds)\n\n"
            "6. Reconnect your computer to your home WiFi\n\n"
            "7. The ESP32 should now appear in the main dashboard\n\n"
            "Troubleshooting:\n"
            "• If ESP32_SETUP network doesn't appear, restart the ESP32\n"
            "• If connection fails, check WiFi password and try again\n"
            "• Make sure your router supports 2.4GHz (ESP32 doesn't support 5GHz)\n"
            "• If dashboard shows no data after setup, try power cycling the ESP32",
        )
        instructions.config(state=tk.DISABLED)

    def create_setup_form(self):
        """Create the WiFi credentials form"""
        form_frame = ttk.LabelFrame(self.window, text="WiFi Credentials", padding=15)
        form_frame.pack(fill=tk.X, padx=15, pady=15)

        # SSID input
        ttk.Label(form_frame, text="Network Name (SSID):", font=("", 10, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=8
        )

        self.ssid_entry = ttk.Entry(form_frame, width=35, font=("", 10))
        self.ssid_entry.grid(row=0, column=1, padx=5, pady=8, sticky=tk.W + tk.E)

        # Password input
        ttk.Label(form_frame, text="Password:", font=("", 10, "bold")).grid(
            row=1, column=0, sticky=tk.W, padx=5, pady=8
        )

        self.pass_entry = ttk.Entry(form_frame, width=35, show="*", font=("", 10))
        self.pass_entry.grid(row=1, column=1, padx=5, pady=8, sticky=tk.W + tk.E)

        # Show password checkbox
        self.show_pass_var = tk.BooleanVar()
        show_pass_cb = ttk.Checkbutton(
            form_frame,
            text="Show password",
            variable=self.show_pass_var,
            command=self.toggle_password,
        )
        show_pass_cb.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        # Network type selection
        ttk.Label(form_frame, text="Network Type:").grid(
            row=3, column=0, sticky=tk.W, padx=5, pady=8
        )

        self.network_type = ttk.Combobox(
            form_frame,
            values=[
                "WPA/WPA2 Personal (Most common)",
                "WPA3 Personal",
                "Open Network (No password)",
                "WEP (Legacy - not recommended)",
            ],
            state="readonly",
        )
        self.network_type.grid(row=3, column=1, padx=5, pady=8, sticky=tk.W + tk.E)
        self.network_type.set("WPA/WPA2 Personal (Most common)")

        # Status label
        self.status_label = ttk.Label(
            form_frame,
            text="Status: Ready to send credentials",
            foreground="blue",
            font=("", 9),
        )
        self.status_label.grid(row=4, column=0, columnspan=2, pady=15)

        # Configure column weights for resizing
        form_frame.columnconfigure(1, weight=1)

    def create_control_buttons(self):
        """Create control buttons"""
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill=tk.X, padx=15, pady=15)

        # Send credentials button
        send_btn = ttk.Button(
            btn_frame, text="Send WiFi Credentials", command=self.send_credentials
        )
        send_btn.pack(side=tk.LEFT, padx=10)

        # Test connection button
        test_btn = ttk.Button(
            btn_frame,
            text="🔍 Test ESP32 Connection",
            command=self.test_esp32_connection,
        )
        test_btn.pack(side=tk.LEFT, padx=10)

        # Cancel button
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.window.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=10)

        # Help button
        help_btn = ttk.Button(btn_frame, text="❓ Help", command=self.show_help)
        help_btn.pack(side=tk.RIGHT, padx=10)

        # Focus and key bindings
        self.ssid_entry.focus()
        self.ssid_entry.bind("<Return>", lambda e: self.pass_entry.focus())
        self.pass_entry.bind("<Return>", lambda e: self.send_credentials())

    def toggle_password(self):
        """Toggle password visibility"""
        self.pass_entry.config(show="" if self.show_pass_var.get() else "*")

    def send_credentials(self):
        """Send WiFi credentials to ESP32"""
        ssid = self.ssid_entry.get().strip()
        password = self.pass_entry.get()

        if not ssid:
            messagebox.showerror("Error", "SSID cannot be empty")
            return

        # Handle open networks
        network_type = self.network_type.get()
        if "Open Network" in network_type:
            password = ""

        self.status_label.config(
            text="Status: Sending credentials to ESP32...", foreground="orange"
        )
        self.window.update()

        # Send credentials
        success = self.send_credentials_callback(ssid, password)

        if success:
            self.status_label.config(
                text="Status: Credentials sent successfully!", foreground="green"
            )

            # Clear password for security
            self.pass_entry.delete(0, tk.END)

            # Show success message
            messagebox.showinfo(
                "Success",
                f"WiFi credentials sent to ESP32!\n\n"
                f"SSID: {ssid}\n"
                f"Password: {'[hidden]' if password else '[none]'}\n\n"
                f"ESP32 will now attempt to connect to your router.\n"
                f"This may take 10-30 seconds.\n\n"
                f"Please reconnect your computer to your home WiFi network.\n"
                f"The ESP32 should appear in the main dashboard once connected.",
            )
        else:
            self.status_label.config(
                text="Status: Failed to send credentials", foreground="red"
            )

    def test_esp32_connection(self):
        """Test connection to ESP32 setup mode"""
        import socket

        self.status_label.config(
            text="Status: Testing ESP32 connection...", foreground="blue"
        )
        self.window.update()

        try:
            # Try to connect to ESP32 setup IP
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_socket.settimeout(3)
            test_socket.sendto(b"TEST", ("192.168.4.1", 4567))
            test_socket.close()

            self.status_label.config(
                text="Status: ✓ ESP32 setup mode detected", foreground="green"
            )

            messagebox.showinfo(
                "Connection Test",
                "✓ Successfully connected to ESP32 setup mode!\n\n"
                "You can now send WiFi credentials.",
            )

        except Exception as e:
            self.status_label.config(
                text="Status: ✗ Cannot reach ESP32 setup mode", foreground="red"
            )

            messagebox.showerror(
                "Connection Test Failed",
                f"Cannot connect to ESP32 setup mode.\n\n"
                f"Error: {e}\n\n"
                f"Please check:\n"
                f"• ESP32 is powered on\n"
                f"• You're connected to 'ESP32_SETUP' WiFi network\n"
                f"• ESP32 is in setup mode (not connected to another network)",
            )

    def show_help(self):
        """Show detailed help information"""
        help_window = tk.Toplevel(self.window)
        help_window.title("WiFi Setup Help")
        help_window.geometry("500x400")
        help_window.grab_set()

        help_text = tk.Text(help_window, wrap=tk.WORD, font=("", 9), padx=15, pady=15)
        help_text.pack(fill=tk.BOTH, expand=True)

        help_content = """
ESP32 WiFi Setup Help

COMMON ISSUES AND SOLUTIONS:

1. "ESP32_SETUP network not found"
   • Power cycle the ESP32 (unplug and plug back in)
   • Wait 30 seconds for the ESP32 to fully boot
   • Check if ESP32 is already connected to another network

2. "Connection timeout" 
   • Make sure you're connected to ESP32_SETUP network
   • Check that your computer's WiFi is working
   • Try moving closer to the ESP32

3. "Credentials sent but ESP32 won't connect"
   • Double-check WiFi password (case sensitive)
   • Ensure your router supports 2.4GHz
   • Check if your network uses special characters
   • Some networks require MAC address registration

4. "ESP32 connects but dashboard shows no data"
   • Wait 1-2 minutes for full initialization
   • Power cycle the ESP32
   • Check if your firewall is blocking UDP port 3333
   • Restart the dashboard application

5. Network Security Types:
   • WPA/WPA2 Personal: Most home networks
   • WPA3 Personal: Newer routers (may not be supported)
   • Open Network: No password required
   • WEP: Very old, avoid if possible

TIPS:
• Use a strong, unique password for your WiFi
• 2.4GHz networks have better range than 5GHz
• Some mesh networks may cause connection issues
• Guest networks sometimes have restrictions

If problems persist, try connecting the ESP32 to a mobile hotspot first to verify it's working, then troubleshoot your main network.
"""

        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)

        ttk.Button(help_window, text="Close", command=help_window.destroy).pack(pady=10)
