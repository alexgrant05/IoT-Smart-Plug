# ESP32 Smart Power Monitor with Auto Calibration

An IoT power monitoring system featuring automatic calibration, device recognition, and real time data visualization.

## Project Overview

This project implements a complete smart plug monitoring solution using an ESP32 microcontroller and SCT-013-000 current transformer. It features auto calibration algorithms, machine learning based device recognition, and a full featured Python dashboard for real time monitoring and data analysis.

### Key Features

- **Auto Calibration System**: Automatically adjusts for circuit variations and sensor drift
- **Device Recognition**: ML based identification of connected devices by their power signatures
- **Real Time Monitoring**: Live power consumption tracking with < 2s latency
- **Professional Dashboard**: Python GUI with graphing, statistics, and calibration controls
- **Data Logging**: Comprehensive CSV/JSON export with auto calibration event tracking
- **WiFi Configuration**: Built-in access point mode for easy network setup
- **Learning System**: Adapts calibration parameters over time for improved accuracy

## Technical Stack

### Hardware
- **Microcontroller**: ESP32 (ESP-WROOM-32)
- **Current Sensor**: SCT-013-000 (100A:50mA current transformer)
- **Burden Resistor**: 10Ω (optimized for sensitivity)
- **ADC**: 12-bit resolution with bias voltage correction
- **Relay**: GPIO-controlled for remote switching

### Software
- **Firmware**: ESP-IDF 5.1.1 (C)
- **Dashboard**: Python 3.13.5 with Tkinter GUI
- **Communication**: UDP broadcast protocol
- **Build System**: PlatformIO

## Circuit Description

The entire circuit is built on a breadboard with the following connections:

### Relay Module Configuration
- Relay VCC → ESP32 5V pin
- Relay GND → ESP32 GND pin
- Relay IN → ESP32 GPIO27
- The "hot wire" of an extension cord is wired through the relay's normally open (NO) contacts, allowing the ESP32 to control power to connected appliances

### SCT-013-000 Current Sensor Circuit
The sensor circuit uses a voltage divider to create a 1.65V bias point for the AC signal:

1. **Voltage Divider Section**:
   - Resistor 1 (10kΩ): Connected from ESP32 3.3V to breadboard row 1
   - Resistor 2 (10kΩ): Connected from breadboard row 1 to row 2
   - GND connection: ESP32 GND pin jumped to row 2

2. **AC Coupling Capacitor**:
   - Capacitor (10µF): Positive leg in row 1, negative leg in row 2
   - This blocks DC while allowing AC signal to pass

3. **Burden Resistor Circuit**:
   - Jumper wire: From row 1 to row 3 (carries biased signal)
   - Burden resistor (10Ω): Connected from row 3 to row 4
   - This converts the SCT-013's current output to voltage

4. **Signal Connections**:
   - SCT-013 output wire → Row 4
   - ESP32 GPIO39 (ADC input) → Row 4
   - This provides the voltage signal to the ESP32's ADC

The circuit creates a DC bias of ~1.65V (half of 3.3V) which allows the AC signal from the current transformer to swing both positive and negative while staying within the ESP32's 0-3.3V ADC range.

## System Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   SCT-013-000   │────▶│      ESP32       │────▶│  Python Dashboard│
│ Current Sensor  │     │   - ADC Reading  │ UDP │   - Real-time   │
└─────────────────┘     │   - Calibration  │     │   - Graphing    │
                        │   - UDP Sender   │     │   - Analysis    │
                        └──────────────────┘     └─────────────────┘
```

## Quick Start

### ESP32 Firmware Setup

1. Install PlatformIO (VS Code extension recommended)
2. Navigate to firmware directory:
   ```bash
   cd firmware
   ```
3. Build and upload:
   ```bash
   pio run -t upload
   ```
4. Monitor serial output:
   ```bash
   pio device monitor
   ```

### Python Dashboard Setup

1. Install Python dependencies:
   ```bash
   cd python_dashboard
   pip install -r requirements.txt
   ```
2. Run the dashboard:
   ```bash
   python app.py
   ```

### Initial Configuration

1. Power on ESP32 - it will create "ESP32_SETUP" WiFi network
2. Connect to this network (password: `esp32pass`)
3. In the dashboard, click "WiFi Setup" and enter your home network credentials
4. ESP32 will restart and connect to your network

## Calibration

The system features multiple calibration methods:

### auto Calibration (Recommended)
- Automatically adjusts bias voltage and scale factor
- Learns from stable load patterns
- Recognizes common devices (60W bulbs, hair dryers, etc.)

### Manual Calibration Options
1. **Known Device Method**: Use a device with known power consumption
2. **Two-Point Calibration**: Zero point + known load for best accuracy
3. **Direct Parameter Setting**: If parameters are known

### Quick Bias Fix
For high readings with no load:
1. Ensure nothing is plugged into the extension cord
2. Click "Fix Bias" button in the dashboard
3. System will recalibrate the DC bias voltage

## Features Breakdown

### auto Calibration System
- **Zero-point drift correction**: Automatically compensates for temperature and component aging
- **Scale factor learning**: Improves accuracy over time based on recognized devices
- **Variance-based detection**: Identifies stable loads for calibration opportunities
- **Configurable sensitivity**: Adjust between conservative and aggressive calibration

### Device Recognition
- Pre-programmed profiles for common appliances
- Pattern matching based on current consumption ranges
- Confidence scoring for reliable identification
- Expandable device database

### Data Analysis
- Real-time power graphing with automatic scaling
- Energy consumption tracking (Wh/kWh)
- Cost estimation based on usage patterns
- Statistical analysis (min/max/average/variance)
- Significant event detection and logging

## Performance Metrics

- **Measurement Range**: 0.1A - 100A (12W - 12kW @ 120V)
- **Accuracy**: ±2% after calibration (typical)
- **Sampling Rate**: ~500 Hz internal, 0.5 Hz reporting
- **Response Time**: < 2 seconds for display updates
- **Calibration Time**: < 10 seconds for zero-point, < 30 seconds for full calibration

## Troubleshooting

### Common Issues

1. **High readings with no load**
   - Solution: Use "Fix Bias" button to recalibrate DC offset
   
2. **ESP32 not connecting to WiFi**
   - Ensure 2.4GHz network (5GHz not supported)
   - Check password (case-sensitive)
   - Try power cycling the ESP32

3. **No data in dashboard**
   - Verify ESP32 IP address in dashboard
   - Check firewall settings (UDP port 3333)
   - Ensure both devices on same network

4. **Erratic readings**
   - Check SCT-013 clamp closure
   - Verify single wire pass-through (not whole cable)
   - Ensure proper burden resistor connection

## Technical Details

### Calibration Mathematics
```
Current (A) = (VRMS - Vbias) × Scale_Factor
where:
- VRMS = RMS voltage from ADC
- Vbias = DC bias voltage (~1.65V typical)
- Scale_Factor = A/V conversion (200 theoretical)
```

### UDP Protocol Format
```
SEQ=1234,TIME=5678,CURRENT=1.234,VOLTAGE_RMS=0.006,POWER=148.08,CAL_STATUS=...
```

## Project Highlights

This project demonstrates:
- **Full-stack IoT development** (embedded + application)
- **Hardware-software integration** with real-world sensors
- **Signal processing** and calibration algorithms
- **Machine learning concepts** in device recognition
- **Professional GUI development** with real-time data visualization
- **Network programming** with UDP and WiFi configuration
- **Data persistence** and analysis capabilities

## Learning Outcomes

Through this project, I gained experience with:
- ESP32 programming with ESP-IDF
- ADC sampling and signal processing
- Current transformer theory and application
- auto calibration algorithm development
- Python GUI development with Tkinter
- Real-time data visualization
- UDP network programming
- IoT system design and integration

