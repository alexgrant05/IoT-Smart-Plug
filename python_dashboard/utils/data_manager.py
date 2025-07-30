import csv
import json
import os
from datetime import datetime


class DataManager:
    """Enhanced data manager with auto-calibration event tracking"""

    def __init__(self):
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)

    def save_csv(self, timestamps, power_values):
        """Save power data to CSV file with auto-calibration markers"""
        if not power_values or len(power_values) == 0:
            print("[DATA] No data to save")
            return False

        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.data_dir, f"power_log_{timestamp_str}.csv")

            with open(filename, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "datetime", "power_watts", "notes"])

                for t, p in zip(timestamps, power_values):
                    dt_str = datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S")

                    # Add notes for significant power changes (could indicate auto-calibration)
                    notes = ""
                    if len(power_values) > 1:
                        idx = list(power_values).index(p)
                        if idx > 0:
                            prev_power = list(power_values)[idx - 1]
                            if abs(p - prev_power) > 50:  # Significant change
                                notes = "significant_change"

                    writer.writerow([f"{t:.6f}", dt_str, f"{p:.2f}", notes])

            print(f"[DATA] Power data saved to {filename}")
            print(f"[DATA] Records: {len(power_values)}")

            # Calculate enhanced statistics
            if len(timestamps) > 1:
                total_time_minutes = (timestamps[-1] - timestamps[0]) / 60
                avg_power = sum(power_values) / len(power_values)
                max_power = max(power_values)
                min_power = min(power_values)
                total_energy_wh = avg_power * (total_time_minutes / 60)

                # Count significant changes (potential auto-calibration events)
                significant_changes = 0
                for i in range(1, len(power_values)):
                    if abs(power_values[i] - power_values[i - 1]) > 50:
                        significant_changes += 1

                print(f"[DATA] Duration: {total_time_minutes:.1f} minutes")
                print(
                    f"[DATA] Power - Avg: {avg_power:.1f}W, Min: {min_power:.1f}W, Max: {max_power:.1f}W"
                )
                print(f"[DATA] Energy consumed: {total_energy_wh:.2f} Wh")
                print(
                    f"[DATA] Significant changes: {significant_changes} (potential calibration events)"
                )

            return True

        except Exception as e:
            print(f"[DATA] Error saving CSV: {e}")
            return False

    def save_auto_cal_events(self, auto_cal_events):
        """Save auto-calibration events to JSON file"""
        if not auto_cal_events:
            return False

        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(
                self.data_dir, f"auto_cal_events_{timestamp_str}.json"
            )

            # Convert events to serializable format
            serializable_events = []
            for event in auto_cal_events:
                serializable_event = {
                    "timestamp": event["timestamp"],
                    "datetime": datetime.fromtimestamp(event["timestamp"]).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "type": event["type"],
                    "stats": event.get("stats", {}),
                }
                serializable_events.append(serializable_event)

            with open(filename, "w") as f:
                json.dump(serializable_events, f, indent=2)

            print(f"[DATA] Auto-calibration events saved to {filename}")
            print(f"[DATA] Events: {len(serializable_events)}")
            return True

        except Exception as e:
            print(f"[DATA] Error saving auto-calibration events: {e}")
            return False

    def save_device_recognitions(self, device_recognitions):
        """Save device recognition events to JSON file"""
        if not device_recognitions:
            return False

        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(
                self.data_dir, f"device_recognitions_{timestamp_str}.json"
            )

            # Convert recognitions to serializable format
            serializable_recognitions = []
            for recognition in device_recognitions:
                serializable_recognition = {
                    "timestamp": recognition["timestamp"],
                    "datetime": datetime.fromtimestamp(
                        recognition["timestamp"]
                    ).strftime("%Y-%m-%d %H:%M:%S"),
                    "current": recognition["current"],
                    "device_info": recognition["device_info"],
                }
                serializable_recognitions.append(serializable_recognition)

            with open(filename, "w") as f:
                json.dump(serializable_recognitions, f, indent=2)

            print(f"[DATA] Device recognitions saved to {filename}")
            print(f"[DATA] Recognitions: {len(serializable_recognitions)}")
            return True

        except Exception as e:
            print(f"[DATA] Error saving device recognitions: {e}")
            return False

    def export_comprehensive_report(
        self, timestamps, power_values, auto_cal_events=None, device_recognitions=None
    ):
        """Export comprehensive report with auto-calibration analysis"""
        if not power_values:
            return False

        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(
                self.data_dir, f"comprehensive_report_{timestamp_str}.txt"
            )

            powers = list(power_values)
            times = list(timestamps)

            total_time_seconds = times[-1] - times[0] if len(times) > 1 else 0
            total_time_hours = total_time_seconds / 3600

            avg_power = sum(powers) / len(powers)
            max_power = max(powers)
            min_power = min(powers)
            median_power = sorted(powers)[len(powers) // 2]

            # Calculate power variance and stability
            variance = sum((p - avg_power) ** 2 for p in powers) / len(powers)
            std_dev = variance**0.5

            # Simple energy calculation
            energy_wh = avg_power * total_time_hours

            # Analyze power distribution
            low_power_count = sum(1 for p in powers if p < 10)
            medium_power_count = sum(1 for p in powers if 10 <= p < 100)
            high_power_count = sum(1 for p in powers if p >= 100)

            # Count significant changes
            significant_changes = []
            for i in range(1, len(powers)):
                if abs(powers[i] - powers[i - 1]) > 50:
                    significant_changes.append(
                        {
                            "timestamp": times[i],
                            "from_power": powers[i - 1],
                            "to_power": powers[i],
                            "change": powers[i] - powers[i - 1],
                        }
                    )

            with open(filename, "w") as f:
                f.write(
                    "ESP32 Smart Plug - Comprehensive Report with Auto-Calibration\n"
                )
                f.write("=" * 65 + "\n\n")
                f.write(
                    f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write(
                    "Features: Auto-Calibration, Device Recognition, Learning System\n\n"
                )

                # MEASUREMENT PERIOD
                f.write("MEASUREMENT PERIOD:\n")
                f.write(
                    f"  Start: {datetime.fromtimestamp(times[0]).strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write(
                    f"  End: {datetime.fromtimestamp(times[-1]).strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                f.write(
                    f"  Duration: {total_time_hours:.2f} hours ({total_time_seconds/60:.1f} minutes)\n"
                )
                f.write(f"  Data Points: {len(powers)}\n")
                f.write(
                    f"  Sampling Rate: {len(powers)/total_time_hours:.1f} samples/hour\n\n"
                )

                # POWER STATISTICS
                f.write("POWER STATISTICS:\n")
                f.write(f"  Average Power: {avg_power:.2f} W\n")
                f.write(f"  Median Power: {median_power:.2f} W\n")
                f.write(f"  Maximum Power: {max_power:.2f} W\n")
                f.write(f"  Minimum Power: {min_power:.2f} W\n")
                f.write(f"  Standard Deviation: {std_dev:.2f} W\n")
                f.write(f"  Power Variance: {variance:.2f} W²\n\n")

                # POWER DISTRIBUTION
                f.write("POWER DISTRIBUTION:\n")
                f.write(
                    f"  Low Power (< 10W): {low_power_count} readings ({100*low_power_count/len(powers):.1f}%)\n"
                )
                f.write(
                    f"  Medium Power (10-100W): {medium_power_count} readings ({100*medium_power_count/len(powers):.1f}%)\n"
                )
                f.write(
                    f"  High Power (≥ 100W): {high_power_count} readings ({100*high_power_count/len(powers):.1f}%)\n\n"
                )

                # ENERGY CONSUMPTION
                f.write("ENERGY CONSUMPTION:\n")
                f.write(
                    f"  Total Energy: {energy_wh:.2f} Wh ({energy_wh/1000:.3f} kWh)\n"
                )

                cost_per_kwh = 0.12
                estimated_cost = (energy_wh / 1000) * cost_per_kwh
                f.write(
                    f"  Estimated Cost: ${estimated_cost:.4f} (at ${cost_per_kwh}/kWh)\n"
                )

                if total_time_hours > 0:
                    daily_energy = energy_wh * (24 / total_time_hours)
                    monthly_energy = daily_energy * 30
                    f.write(f"  Projected Daily: {daily_energy:.2f} Wh\n")
                    f.write(
                        f"  Projected Monthly: {monthly_energy/1000:.2f} kWh (${monthly_energy/1000*cost_per_kwh:.2f})\n\n"
                    )

                # SIGNIFICANT CHANGES ANALYSIS
                f.write("POWER CHANGE ANALYSIS:\n")
                f.write(f"  Significant Changes (>50W): {len(significant_changes)}\n")
                if significant_changes:
                    f.write("  Top 5 Largest Changes:\n")
                    sorted_changes = sorted(
                        significant_changes,
                        key=lambda x: abs(x["change"]),
                        reverse=True,
                    )[:5]
                    for i, change in enumerate(sorted_changes, 1):
                        change_time = datetime.fromtimestamp(
                            change["timestamp"]
                        ).strftime("%H:%M:%S")
                        f.write(
                            f"    {i}. {change_time}: {change['from_power']:.1f}W → {change['to_power']:.1f}W ({change['change']:+.1f}W)\n"
                        )
                f.write("\n")

                # AUTO-CALIBRATION EVENTS
                if auto_cal_events:
                    f.write("AUTO-CALIBRATION EVENTS:\n")
                    f.write(f"  Total Events: {len(auto_cal_events)}\n")

                    # Group events by type
                    event_types = {}
                    for event in auto_cal_events:
                        event_type = event["type"]
                        if event_type not in event_types:
                            event_types[event_type] = []
                        event_types[event_type].append(event)

                    for event_type, events in event_types.items():
                        f.write(f"    {event_type}: {len(events)} times\n")

                    f.write("  Recent Events:\n")
                    recent_events = sorted(
                        auto_cal_events, key=lambda x: x["timestamp"], reverse=True
                    )[:5]
                    for event in recent_events:
                        event_time = datetime.fromtimestamp(
                            event["timestamp"]
                        ).strftime("%m-%d %H:%M:%S")
                        f.write(f"    {event_time}: {event['type']}\n")
                    f.write("\n")

                # DEVICE RECOGNITION
                if device_recognitions:
                    f.write("DEVICE RECOGNITION:\n")
                    f.write(f"  Total Recognitions: {len(device_recognitions)}\n")

                    # Group by device
                    devices = {}
                    for recognition in device_recognitions:
                        device_info = recognition["device_info"]
                        if device_info not in devices:
                            devices[device_info] = []
                        devices[device_info].append(recognition)

                    f.write("  Recognized Devices:\n")
                    for device_info, recognitions in devices.items():
                        avg_current = sum(r["current"] for r in recognitions) / len(
                            recognitions
                        )
                        f.write(
                            f"    {device_info}: {len(recognitions)} times (avg: {avg_current:.2f}A)\n"
                        )
                    f.write("\n")

                # SYSTEM PERFORMANCE
                f.write("SYSTEM PERFORMANCE:\n")
                stability_score = (
                    max(0, 100 - (std_dev / avg_power * 100)) if avg_power > 0 else 0
                )
                f.write(f"  Measurement Stability: {stability_score:.1f}%\n")

                if len(significant_changes) > 0:
                    change_frequency = len(significant_changes) / total_time_hours
                    f.write(
                        f"  Change Frequency: {change_frequency:.2f} significant changes/hour\n"
                    )

                data_completeness = (
                    len(powers) / (total_time_seconds / 2)
                ) * 100  # Assuming 2-second intervals
                f.write(f"  Data Completeness: {min(100, data_completeness):.1f}%\n\n")

                # RECOMMENDATIONS
                f.write("RECOMMENDATIONS:\n")
                if std_dev / avg_power > 0.5 if avg_power > 0 else False:
                    f.write(
                        "  • High power variability detected - consider device recognition tuning\n"
                    )
                if len(significant_changes) > 10:
                    f.write(
                        "  • Frequent power changes - auto-calibration is adapting well\n"
                    )
                if avg_power < 5:
                    f.write("  • Low average power - mostly standby or light loads\n")
                elif avg_power > 500:
                    f.write("  • High average power - heavy appliance usage detected\n")

                if auto_cal_events and len(auto_cal_events) > 0:
                    f.write("  • Auto-calibration system is active and learning\n")
                else:
                    f.write(
                        "  • Consider enabling auto-calibration for better accuracy\n"
                    )

                f.write("\n")
                f.write(
                    "This report was generated by ESP32 Smart Plug with Auto-Calibration\n"
                )
                f.write("SCT-013-000 Current Transformer with 10Ω Burden Resistor\n")

            print(f"[DATA] Comprehensive report saved to {filename}")
            return True

        except Exception as e:
            print(f"[DATA] Error creating comprehensive report: {e}")
            return False

    def load_historical_data(self, days_back=7):
        """Load historical data files for analysis"""
        try:
            import glob
            from datetime import datetime, timedelta

            cutoff_date = datetime.now() - timedelta(days=days_back)

            power_files = glob.glob(os.path.join(self.data_dir, "power_log_*.csv"))
            auto_cal_files = glob.glob(
                os.path.join(self.data_dir, "auto_cal_events_*.json")
            )

            historical_data = {"power_data": [], "auto_cal_events": [], "summary": {}}

            # Load power data
            for file_path in power_files:
                file_date_str = os.path.basename(file_path).split("_")[2:4]
                file_date_str = "_".join(file_date_str).replace(".csv", "")
                try:
                    file_date = datetime.strptime(file_date_str, "%Y%m%d_%H%M%S")
                    if file_date >= cutoff_date:
                        with open(file_path, "r") as f:
                            reader = csv.DictReader(f)
                            for row in reader:
                                historical_data["power_data"].append(
                                    {
                                        "timestamp": float(row["timestamp"]),
                                        "power": float(row["power_watts"]),
                                        "file_date": file_date,
                                    }
                                )
                except:
                    continue

            # Load auto-calibration events
            for file_path in auto_cal_files:
                file_date_str = os.path.basename(file_path).split("_")[3:5]
                file_date_str = "_".join(file_date_str).replace(".json", "")
                try:
                    file_date = datetime.strptime(file_date_str, "%Y%m%d_%H%M%S")
                    if file_date >= cutoff_date:
                        with open(file_path, "r") as f:
                            events = json.load(f)
                            historical_data["auto_cal_events"].extend(events)
                except:
                    continue

            # Generate summary
            historical_data["summary"] = {
                "total_power_readings": len(historical_data["power_data"]),
                "total_auto_cal_events": len(historical_data["auto_cal_events"]),
                "date_range_days": days_back,
                "files_processed": len(power_files) + len(auto_cal_files),
            }

            print(
                f"[DATA] Loaded {len(historical_data['power_data'])} power readings and {len(historical_data['auto_cal_events'])} auto-cal events"
            )
            return historical_data

        except Exception as e:
            print(f"[DATA] Error loading historical data: {e}")
            return None

    def analyze_auto_cal_performance(self, auto_cal_events):
        """Analyze auto-calibration performance metrics"""
        if not auto_cal_events:
            return None

        try:
            analysis = {
                "total_events": len(auto_cal_events),
                "event_types": {},
                "frequency_analysis": {},
                "performance_metrics": {},
            }

            # Count event types
            for event in auto_cal_events:
                event_type = event.get("type", "unknown")
                analysis["event_types"][event_type] = (
                    analysis["event_types"].get(event_type, 0) + 1
                )

            # Frequency analysis
            if len(auto_cal_events) > 1:
                timestamps = [event["timestamp"] for event in auto_cal_events]
                time_span = max(timestamps) - min(timestamps)
                analysis["frequency_analysis"] = {
                    "time_span_hours": time_span / 3600,
                    "average_interval_minutes": (time_span / len(auto_cal_events)) / 60,
                    "events_per_hour": (
                        len(auto_cal_events) / (time_span / 3600)
                        if time_span > 0
                        else 0
                    ),
                }

            # Performance metrics
            analysis["performance_metrics"] = {
                "calibration_activity_level": (
                    "high"
                    if len(auto_cal_events) > 10
                    else "moderate" if len(auto_cal_events) > 3 else "low"
                ),
                "most_common_event": (
                    max(analysis["event_types"], key=analysis["event_types"].get)
                    if analysis["event_types"]
                    else "none"
                ),
            }

            return analysis

        except Exception as e:
            print(f"[DATA] Error analyzing auto-calibration performance: {e}")
            return None
