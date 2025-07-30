def animate_graph(
    frame, ax, line, current_label, stats_label, timestamps, power_values
):
    """Enhanced graph animation with better visuals for SCT-013-000"""

    if len(timestamps) < 2:
        ax.clear()
        ax.set_title(
            "Real-Time Power Usage (SCT-013-000)", fontsize=14, fontweight="bold"
        )
        ax.set_ylabel("Power (Watts)")
        ax.set_xlabel("Time (seconds)")
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.text(
            0.5,
            0.5,
            "Waiting for data from ESP32...\n\nMake sure:\n• ESP32 is connected\n• SCT-013 is properly clamped\n• Extension cord is plugged in",
            horizontalalignment="center",
            verticalalignment="center",
            transform=ax.transAxes,
            fontsize=12,
            alpha=0.7,
        )

        current_label.config(text="--- W")
        stats_label.config(text="Stats: Waiting for data from ESP32...")
        return (line,)

    try:
        # Calculate relative timestamps
        t0 = timestamps[0]
        times = [t - t0 for t in timestamps]
        powers = list(power_values)

        # Clear and redraw
        ax.clear()

        # Plot main line
        ax.plot(times, powers, color="#2E86AB", linewidth=2.5, alpha=0.8, label="Power")

        # Highlight current point
        if len(powers) > 0:
            ax.scatter(
                times[-1],
                powers[-1],
                color="#F24236",
                s=80,
                zorder=5,
                edgecolors="white",
                linewidth=2,
            )

        # Enhanced title and labels
        ax.set_title(
            "Real-Time Power Usage (SCT-013-000 with 10Ω Burden)",
            fontsize=14,
            fontweight="bold",
            color="#2C3E50",
        )
        ax.set_ylabel("Power (Watts)", fontsize=12)
        ax.set_xlabel("Time (seconds)", fontsize=12)

        # Smart Y-axis scaling
        max_power = max(powers) if powers else 0
        min_power = min(powers) if powers else 0

        # Set appropriate scale based on power range
        if max_power < 10:
            y_max = 10  # For small loads
        elif max_power < 100:
            y_max = max(100, max_power * 1.2)  # For typical household loads
        elif max_power < 1000:
            y_max = max_power * 1.15  # For medium loads
        else:
            y_max = max_power * 1.1  # For high loads

        ax.set_ylim(0, y_max)

        # Enhanced grid and background
        ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)
        ax.set_facecolor("#FAFAFA")

        # Add power level indicators
        if y_max > 50:
            ax.axhspan(0, 10, alpha=0.05, color="green", label="Standby")
            ax.axhspan(10, 100, alpha=0.05, color="blue", label="Light Load")
            if y_max > 500:
                ax.axhspan(100, 500, alpha=0.05, color="orange", label="Medium Load")
                ax.axhspan(500, y_max, alpha=0.05, color="red", label="Heavy Load")

        # Update current power display with enhanced formatting
        current_power = powers[-1]
        current_label.config(text=f"{current_power:.1f} W")

        # Enhanced color coding
        if current_power < 1:
            color = "#888888"  # Gray for no/minimal load
            status = "No Load"
        elif current_power < 10:
            color = "#27AE60"  # Green for standby
            status = "Standby"
        elif current_power < 100:
            color = "#3498DB"  # Blue for light load
            status = "Light Load"
        elif current_power < 500:
            color = "#F39C12"  # Orange for medium load
            status = "Medium Load"
        else:
            color = "#E74C3C"  # Red for heavy load
            status = "Heavy Load"

        current_label.config(foreground=color)

        # Calculate enhanced statistics
        min_power = min(powers)
        max_power = max(powers)
        avg_power = sum(powers) / len(powers)

        # Calculate energy consumption (simple integration)
        if len(times) > 1:
            time_span_hours = (times[-1] - times[0]) / 3600  # Convert to hours
            energy_wh = avg_power * time_span_hours
        else:
            energy_wh = 0

        # Calculate trend (last 10 points vs previous 10)
        if len(powers) >= 20:
            recent = powers[-10:]
            previous = powers[-20:-10]
            recent_avg = sum(recent) / len(recent)
            previous_avg = sum(previous) / len(previous)

            if recent_avg > previous_avg * 1.05:
                trend = "↗ Rising"
            elif recent_avg < previous_avg * 0.95:
                trend = "↘ Falling"
            else:
                trend = "→ Stable"
        else:
            trend = "→ Stable"

        # Update stats display with enhanced information
        stats_text = (
            f"{status} • Min: {min_power:.1f}W • Max: {max_power:.1f}W • "
            f"Avg: {avg_power:.1f}W • Energy: {energy_wh:.2f}Wh • {trend} • "
            f"Points: {len(powers)}"
        )
        stats_label.config(text=stats_text)

        # Add time annotation
        if len(times) > 1:
            duration_min = (times[-1] - times[0]) / 60
            ax.text(
                0.02,
                0.98,
                f"Duration: {duration_min:.1f} min",
                transform=ax.transAxes,
                fontsize=9,
                verticalalignment="top",
                alpha=0.7,
            )

        # Add current value annotation
        if len(powers) > 0:
            ax.text(
                0.98,
                0.98,
                f"Current: {current_power:.1f}W",
                transform=ax.transAxes,
                fontsize=10,
                fontweight="bold",
                horizontalalignment="right",
                verticalalignment="top",
                bbox=dict(
                    boxstyle="round,pad=0.3",
                    facecolor=color,
                    alpha=0.7,
                    edgecolor="none",
                ),
                color="white",
            )

    except Exception as e:
        print(f"[GRAPH] Animation error: {e}")
        current_label.config(text="Error")
        stats_label.config(text=f"Stats: Display error - {str(e)[:50]}...")

    return (line,)
