#ifndef HARDWARE_CONFIG_H
#define HARDWARE_CONFIG_H

#include "driver/gpio.h"
#include "esp_adc/adc_oneshot.h"

#define RELAY_GPIO GPIO_NUM_27
#define UDP_SEND_PORT 3333
#define UDP_RECV_PORT 3334
#define WIFI_CREDENTIALS_PORT 4567

#define ENABLE_LOGGING 1
#define USE_CUSTOM_CALIBRATION 0

#if USE_CUSTOM_CALIBRATION
    #define CUSTOM_BIAS_VOLTAGE 1.65f
    #define CUSTOM_AMPS_PER_VOLT 200.0f  // Updated for SCT-013-000 with 10Ω
#endif

// ADC Settings
#define ADC_CHANNEL ADC_CHANNEL_3             // GPIO39
#define ADC_RESOLUTION 4095.0f
#define ADC_VOLTAGE_RANGE 3.3f
#define ADC_GPIO_PIN 39
#define ADC_BIAS_VOLTAGE 1.65f                // Half of 3.3V for AC coupling
#define MAX_CURRENT_AMPS 100.0f

// SCT-013-000 Sensor Configuration
#define SCT_013_BURDEN_RESISTOR 10.0f         // Your 10Ω burden resistor
#define SCT_013_MAX_SECONDARY_CURRENT 0.05f   // 50mA maximum
#define SCT_013_TRANSFORMATION_RATIO 2000.0f  // 2000:1
#define SCT_013_MAX_SECONDARY_VOLTAGE 0.5f    // 50mA × 10Ω = 0.5V RMS
#define SCT_013_THEORETICAL_SCALE 200.0f      // 100A / 0.5V = 200 A/V

// Auto-calibration settings
#define AUTO_CAL_ENABLED 1
#define AUTO_CAL_ZERO_INTERVAL_MS (30 * 60 * 1000)  // 30 minutes
#define AUTO_CAL_MIN_STABLE_READINGS 100             // ~3 minutes at 2s intervals
#define AUTO_CAL_VARIANCE_THRESHOLD 0.1f             // Current stability threshold
#define AUTO_CAL_MIN_CURRENT 0.5f                    // Minimum current for scale calibration
#define AUTO_CAL_MAX_CURRENT 15.0f                   // Maximum current for scale calibration
#define AUTO_CAL_ZERO_THRESHOLD 0.05f                // Below this = zero current
#define AUTO_CAL_CONSECUTIVE_ZERO_COUNT 150          // Readings before zero recalibration

// Learning parameters
#define ENABLE_CALIBRATION_LEARNING 1
#define MAX_LEARNING_POINTS 50
#define LEARNING_CONFIDENCE_DECAY 0.95f              // Older points become less important
#define MIN_LEARNING_POINTS 3                        // Minimum points before learning kicks in

// Device recognition thresholds
#define ENABLE_DEVICE_RECOGNITION 1
#define DEVICE_RECOGNITION_CONFIDENCE 0.9f           // How certain we need to be
#define DEVICE_STABLE_TIME_MS (3 * 60 * 1000)       // 3 minutes of stable operation

#endif