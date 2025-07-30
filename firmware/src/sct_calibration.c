#include "sct_calibration.h"
#include "hardware_config.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_adc/adc_oneshot.h"
#include "lwip/sockets.h"
#include <math.h>
#include <string.h>

static const char *TAG = "SCT_CAL";

// External ADC handle - now defined in main.c
extern adc_oneshot_unit_handle_t adc1_handle;

// Global calibration values
static float amps_per_volt = 200.0f;  // SCT-013-000 with 10Ω burden
static float bias_voltage = 1.65f;    // Half of 3.3V for AC coupling

// Auto-detection state
static bool auto_detection_enabled = true;
static bool auto_calibration_enabled = AUTO_CAL_ENABLED;
static float detected_load_amps = 0.0f;

// Auto-calibration state
static uint32_t last_zero_calibration = 0;
static uint32_t last_scale_calibration = 0;
static uint32_t consecutive_zero_readings = 0;
static float auto_cal_sensitivity = 0.7f;  // Default moderate sensitivity
static float learning_rate = 0.1f;

// Learning system
#if ENABLE_CALIBRATION_LEARNING
static calibration_point_t learning_points[MAX_LEARNING_POINTS];
static int learning_point_count = 0;
static int learning_point_index = 0;  // Circular buffer index
#endif

// Device recognition profiles
#if ENABLE_DEVICE_RECOGNITION
static const device_profile_t known_devices[] = {
    {0.4f, 0.7f, 0.5f, "60W Incandescent Bulb", 1.2f},
    {0.8f, 1.2f, 1.0f, "100W Incandescent Bulb", 1.2f},
    {4.0f, 6.0f, 5.0f, "Hair Dryer Low Setting", 1.5f},
    {10.0f, 15.0f, 12.5f, "Hair Dryer High Setting", 1.5f},
    {8.0f, 12.0f, 10.0f, "Space Heater", 1.3f},
    {12.0f, 16.0f, 14.0f, "Microwave Oven", 1.4f},
    {6.0f, 10.0f, 8.0f, "Coffee Maker", 1.1f},
    {0.1f, 0.3f, 0.2f, "LED Strip/Small Electronics", 0.8f},
    {2.0f, 4.0f, 3.0f, "Laptop/Monitor", 0.9f},
    {0.02f, 0.1f, 0.05f, "Phone Charger/Standby", 0.5f}
};
static const int num_known_devices = sizeof(known_devices) / sizeof(known_devices[0]);
#endif

// Statistics
static uint32_t auto_cal_count = 0;
static uint32_t last_auto_cal_time = 0;
static uint32_t successful_recognitions = 0;
static uint32_t failed_recognitions = 0;

// Current reading history for pattern analysis
#define HISTORY_SIZE 50
static float current_history[HISTORY_SIZE];
static int history_index = 0;
static bool history_full = false;

// Global mutex for thread-safe access
static SemaphoreHandle_t calibration_mutex = NULL;

void sct_calibration_init() {
    calibration_mutex = xSemaphoreCreateMutex();
    if (calibration_mutex == NULL) {
        ESP_LOGE(TAG, "Failed to create calibration mutex");
        return;
    }
    
    ESP_LOGI(TAG, "SCT calibration initialized with auto-calibration");
    ESP_LOGI(TAG, "Initial values - Bias: %.4fV, Scale: %.1fA/V", bias_voltage, amps_per_volt);
    ESP_LOGI(TAG, "Auto-calibration: %s", auto_calibration_enabled ? "ENABLED" : "DISABLED");
    ESP_LOGI(TAG, "Device recognition: %s", ENABLE_DEVICE_RECOGNITION ? "ENABLED" : "DISABLED");
    ESP_LOGI(TAG, "Learning system: %s", ENABLE_CALIBRATION_LEARNING ? "ENABLED" : "DISABLED");
    
    // Initialize learning system
#if ENABLE_CALIBRATION_LEARNING
    memset(learning_points, 0, sizeof(learning_points));
    learning_point_count = 0;
    learning_point_index = 0;
#endif
    
    // Initialize history
    memset(current_history, 0, sizeof(current_history));
    history_index = 0;
    history_full = false;
    
    // Perform automatic zero-point calibration on startup
    ESP_LOGI(TAG, "Performing automatic zero-point calibration...");
    vTaskDelay(pdMS_TO_TICKS(1000)); // Wait for ADC to stabilize
    
    // Auto-calibrate bias voltage with no load
    auto_calibrate_bias_voltage();
    
    // Start auto-calibration task
    if (auto_calibration_enabled) {
        xTaskCreate(auto_calibration_task, "auto_calibration", 4096, NULL, 3, NULL);
        ESP_LOGI(TAG, "Auto-calibration task started");
    }
}

void auto_calibration_task(void *parameters) {
    ESP_LOGI(TAG, "Auto-calibration task running");
    
    while (auto_calibration_enabled) {
        // Check for periodic zero-point calibration
        if (should_auto_calibrate_zero()) {
            ESP_LOGI(TAG, "Performing automatic zero-point recalibration");
            auto_calibrate_bias_voltage();
            last_zero_calibration = xTaskGetTickCount() * portTICK_PERIOD_MS;
            auto_cal_count++;
        }
        
        // Apply learned calibration if enough data points
#if ENABLE_CALIBRATION_LEARNING
        if (learning_point_count >= MIN_LEARNING_POINTS) {
            apply_learned_calibration();
        }
#endif
        
        // Adaptive threshold adjustment based on recent performance
        adaptive_threshold_adjustment();
        
        // Sleep for 30 seconds before next check
        vTaskDelay(pdMS_TO_TICKS(30000));
    }
    
    ESP_LOGI(TAG, "Auto-calibration task ended");
    vTaskDelete(NULL);
}

void process_current_for_auto_calibration(float current_amps) {
    if (!auto_calibration_enabled) {
        return;
    }
    
    // Update current history
    current_history[history_index] = current_amps;
    history_index = (history_index + 1) % HISTORY_SIZE;
    if (history_index == 0) {
        history_full = true;
    }
    
    // Update detected load
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        detected_load_amps = current_amps;
        xSemaphoreGive(calibration_mutex);
    }
    
    // Process for auto-calibration
    continuous_auto_calibration(current_amps);
}

void continuous_auto_calibration(float current_reading) {
    static uint32_t stable_load_start = 0;
    static float stable_load_value = 0;
    static bool in_stable_period = false;
    
    // Check for zero readings (potential drift correction)
    if (current_reading < AUTO_CAL_ZERO_THRESHOLD) {
        consecutive_zero_readings++;
    } else {
        consecutive_zero_readings = 0;
        
        // Check for stable load pattern
        if (history_full) {
            float variance = 0, mean = 0;
            
            // Calculate mean
            for (int i = 0; i < HISTORY_SIZE; i++) {
                mean += current_history[i];
            }
            mean /= HISTORY_SIZE;
            
            // Calculate variance
            for (int i = 0; i < HISTORY_SIZE; i++) {
                float diff = current_history[i] - mean;
                variance += diff * diff;
            }
            variance /= HISTORY_SIZE;
            
            // Check if load is stable and significant
            bool is_stable = (variance < AUTO_CAL_VARIANCE_THRESHOLD) && 
                           (mean >= AUTO_CAL_MIN_CURRENT) && 
                           (mean <= AUTO_CAL_MAX_CURRENT);
            
            if (is_stable && !in_stable_period) {
                // Start of stable period
                stable_load_start = xTaskGetTickCount() * portTICK_PERIOD_MS;
                stable_load_value = mean;
                in_stable_period = true;
                ESP_LOGI(TAG, "Stable load detected: %.3fA", stable_load_value);
                
#if ENABLE_DEVICE_RECOGNITION
                // Try to recognize the device
                auto_recognize_and_calibrate(stable_load_value);
#endif
                
            } else if (is_stable && in_stable_period) {
                // Continue stable period - check if enough time has passed
                uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
                if (now - stable_load_start > DEVICE_STABLE_TIME_MS) {
                    // Long enough stable period for automatic calibration
                    uint32_t time_since_last = now - last_scale_calibration;
                    
                    // Only auto-calibrate if it's been a while since last calibration
                    if (time_since_last > AUTO_CAL_ZERO_INTERVAL_MS) {
                        ESP_LOGI(TAG, "Auto-calibrating with stable load: %.3fA", stable_load_value);
                        calibrate_with_known_load(stable_load_value);
                        last_scale_calibration = now;
                        auto_cal_count++;
                        
#if ENABLE_CALIBRATION_LEARNING
                        // Add to learning system as auto-generated point
                        float measured_vrms = stable_load_value / get_amps_per_volt(); // Approximate
                        learn_from_calibration(stable_load_value, measured_vrms, false);
#endif
                    }
                    in_stable_period = false; // Reset to avoid repeated calibrations
                }
            } else if (!is_stable) {
                // No longer stable
                in_stable_period = false;
            }
        }
    }
}

#if ENABLE_DEVICE_RECOGNITION
void auto_recognize_and_calibrate(float measured_current) {
    const device_profile_t* device = recognize_device(measured_current);
    
    if (device != NULL) {
        ESP_LOGI(TAG, "Auto-recognized device: %s (%.2fA typical)", 
                 device->device_name, device->typical_current);
        
        // Calculate confidence based on how well it matches
        float match_quality = 1.0f - (fabsf(measured_current - device->typical_current) / 
                                     (device->max_current - device->min_current));
        float confidence = match_quality * device->confidence_boost * auto_cal_sensitivity;
        
        // Only auto-calibrate if confidence is high enough
        if (confidence > DEVICE_RECOGNITION_CONFIDENCE) {
            ESP_LOGI(TAG, "High confidence (%.2f), auto-calibrating with %.2fA", 
                     confidence, device->typical_current);
            
            calibrate_with_known_load(device->typical_current);
            successful_recognitions++;
            
#if ENABLE_CALIBRATION_LEARNING
            // Add to learning system with high confidence
            float measured_vrms = measured_current / get_amps_per_volt(); // Approximate
            learn_from_calibration(device->typical_current, measured_vrms, false);
#endif
        } else {
            ESP_LOGI(TAG, "Low confidence (%.2f), skipping auto-calibration", confidence);
            failed_recognitions++;
        }
    }
}

const device_profile_t* recognize_device(float current_amps) {
    for (int i = 0; i < num_known_devices; i++) {
        if (current_amps >= known_devices[i].min_current && 
            current_amps <= known_devices[i].max_current) {
            return &known_devices[i];
        }
    }
    return NULL;
}

void list_known_devices(char* buffer, size_t buffer_size) {
    if (!buffer || buffer_size == 0) return;
    
    int offset = 0;
    offset += snprintf(buffer + offset, buffer_size - offset, "Known devices:\n");
    
    for (int i = 0; i < num_known_devices && offset < buffer_size - 50; i++) {
        offset += snprintf(buffer + offset, buffer_size - offset,
                          "  %s: %.1f-%.1fA (typ: %.1fA)\n",
                          known_devices[i].device_name,
                          known_devices[i].min_current,
                          known_devices[i].max_current,
                          known_devices[i].typical_current);
    }
}
#endif

#if ENABLE_CALIBRATION_LEARNING
void learn_from_calibration(float expected_current, float measured_voltage, bool manual) {
    if (learning_point_count < MAX_LEARNING_POINTS) {
        learning_points[learning_point_count] = (calibration_point_t){
            .expected_current = expected_current,
            .measured_voltage = measured_voltage,
            .timestamp = xTaskGetTickCount() * portTICK_PERIOD_MS,
            .confidence = manual ? 1.0f : 0.8f,  // Manual calibrations get higher confidence
            .auto_generated = !manual
        };
        learning_point_count++;
    } else {
        // Circular buffer - replace oldest
        learning_points[learning_point_index] = (calibration_point_t){
            .expected_current = expected_current,
            .measured_voltage = measured_voltage,
            .timestamp = xTaskGetTickCount() * portTICK_PERIOD_MS,
            .confidence = manual ? 1.0f : 0.8f,
            .auto_generated = !manual
        };
        learning_point_index = (learning_point_index + 1) % MAX_LEARNING_POINTS;
    }
    
    ESP_LOGI(TAG, "Learning point added: %.3fA -> %.6fV (%s)", 
             expected_current, measured_voltage, manual ? "manual" : "auto");
}

void apply_learned_calibration(void) {
    if (learning_point_count < MIN_LEARNING_POINTS) {
        return;
    }
    
    float numerator = 0, denominator = 0, total_weight = 0;
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    
    // Calculate weighted average with time decay
    int points_to_use = (learning_point_count < MAX_LEARNING_POINTS) ? 
                        learning_point_count : MAX_LEARNING_POINTS;
    
    for (int i = 0; i < points_to_use; i++) {
        uint32_t age_ms = now - learning_points[i].timestamp;
        float age_factor = powf(LEARNING_CONFIDENCE_DECAY, age_ms / (24 * 60 * 60 * 1000.0f)); // Daily decay
        float weight = learning_points[i].confidence * age_factor * learning_rate;
        
        if (learning_points[i].measured_voltage > 0.001f) { // Avoid division by very small numbers
            numerator += learning_points[i].expected_current * weight;
            denominator += learning_points[i].measured_voltage * weight;
            total_weight += weight;
        }
    }
    
    if (denominator > 0.001f && total_weight > 0.1f) {
        float learned_scale = numerator / denominator;
        float current_scale = get_amps_per_volt();
        
        // Only apply if the change is reasonable (within 50% of current value)
        if (learned_scale > current_scale * 0.5f && learned_scale < current_scale * 1.5f) {
            // Smooth transition - don't jump immediately to learned value
            float blended_scale = current_scale * 0.7f + learned_scale * 0.3f;
            set_amps_per_volt(blended_scale);
            
            ESP_LOGI(TAG, "Applied learned calibration: %.2f -> %.2f A/V (weight: %.2f)", 
                     current_scale, blended_scale, total_weight);
        } else {
            ESP_LOGW(TAG, "Learned scale %.2f A/V rejected (too different from current %.2f A/V)", 
                     learned_scale, current_scale);
        }
    }
}

void reset_learning_data(void) {
    memset(learning_points, 0, sizeof(learning_points));
    learning_point_count = 0;
    learning_point_index = 0;
    ESP_LOGI(TAG, "Learning data reset");
}

int get_learning_point_count(void) {
    return learning_point_count;
}
#endif

bool should_auto_calibrate_zero(void) {
    if (!auto_calibration_enabled) {
        return false;
    }
    
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    
    // Time-based check (every 30 minutes max)
    bool time_for_calibration = (now - last_zero_calibration) > AUTO_CAL_ZERO_INTERVAL_MS;
    
    // Zero readings check (consistent zeros for extended period)
    bool consistent_zeros = consecutive_zero_readings > AUTO_CAL_CONSECUTIVE_ZERO_COUNT;
    
    return time_for_calibration && consistent_zeros;
}

void adaptive_threshold_adjustment(void) {
    // Adjust sensitivity based on recent performance
    static uint32_t last_adjustment = 0;
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    
    // Only adjust every hour
    if (now - last_adjustment < (60 * 60 * 1000)) {
        return;
    }
    
#if ENABLE_DEVICE_RECOGNITION
    float success_rate = (successful_recognitions + failed_recognitions > 0) ?
                        (float)successful_recognitions / (successful_recognitions + failed_recognitions) : 0.5f;
    
    // Adjust sensitivity based on success rate
    if (success_rate > 0.8f && auto_cal_sensitivity < 0.9f) {
        auto_cal_sensitivity += 0.05f; // Increase sensitivity if doing well
        ESP_LOGI(TAG, "Increased auto-cal sensitivity to %.2f (success rate: %.2f)", 
                 auto_cal_sensitivity, success_rate);
    } else if (success_rate < 0.4f && auto_cal_sensitivity > 0.3f) {
        auto_cal_sensitivity -= 0.05f; // Decrease sensitivity if performing poorly
        ESP_LOGI(TAG, "Decreased auto-cal sensitivity to %.2f (success rate: %.2f)", 
                 auto_cal_sensitivity, success_rate);
    }
    
    last_adjustment = now;
#endif
}

// Configuration functions
void set_auto_cal_sensitivity(float sensitivity) {
    if (sensitivity >= 0.0f && sensitivity <= 1.0f) {
        auto_cal_sensitivity = sensitivity;
        ESP_LOGI(TAG, "Auto-calibration sensitivity set to %.2f", sensitivity);
    }
}

float get_auto_cal_sensitivity(void) {
    return auto_cal_sensitivity;
}

void set_learning_rate(float rate) {
    if (rate >= 0.0f && rate <= 1.0f) {
        learning_rate = rate;
        ESP_LOGI(TAG, "Learning rate set to %.2f", rate);
    }
}

float get_learning_rate(void) {
    return learning_rate;
}

void get_auto_cal_statistics(char* buffer, size_t buffer_size) {
    if (!buffer || buffer_size == 0) return;
    
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    uint32_t uptime_hours = now / (60 * 60 * 1000);
    
    snprintf(buffer, buffer_size,
             "AUTO_CAL_STATS:ENABLED=%s,COUNT=%lu,UPTIME=%luh,SUCCESS=%lu,FAILED=%lu,LEARNING_PTS=%d,SENSITIVITY=%.2f",
             auto_calibration_enabled ? "YES" : "NO",
             auto_cal_count,
             uptime_hours,
             successful_recognitions,
             failed_recognitions,
#if ENABLE_CALIBRATION_LEARNING
             learning_point_count,
#else
             0,
#endif
             auto_cal_sensitivity);
}

uint32_t get_last_auto_cal_time(void) {
    return last_auto_cal_time;
}

uint32_t get_auto_cal_count(void) {
    return auto_cal_count;
}

void reset_auto_cal_statistics(void) {
    auto_cal_count = 0;
    successful_recognitions = 0;
    failed_recognitions = 0;
    last_auto_cal_time = 0;
    ESP_LOGI(TAG, "Auto-calibration statistics reset");
}

// Existing functions with auto-calibration integration...
void set_auto_calibration(bool enabled) {
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        auto_calibration_enabled = enabled;
        xSemaphoreGive(calibration_mutex);
        ESP_LOGI(TAG, "Auto-calibration %s", enabled ? "enabled" : "disabled");
        
        // Start/stop auto-calibration task
        if (enabled) {
            xTaskCreate(auto_calibration_task, "auto_calibration", 4096, NULL, 3, NULL);
        }
    }
}

void set_auto_detection(bool enabled) {
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        auto_detection_enabled = enabled;
        xSemaphoreGive(calibration_mutex);
        ESP_LOGI(TAG, "Auto-detection %s", enabled ? "enabled" : "disabled");
    }
}

bool get_auto_calibration_enabled(void) {
    return auto_calibration_enabled;
}

bool get_auto_detection_enabled(void) {
    return auto_detection_enabled;
}

float get_detected_load_amps(void) {
    float load = 0.0f;
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        load = detected_load_amps;
        xSemaphoreGive(calibration_mutex);
    }
    return load;
}

void auto_detect_load_current(void) {
    if (!auto_detection_enabled) {
        return;
    }
    
    ESP_LOGI(TAG, "Auto-detecting load current...");
    
    const int num_samples = 20;
    float total = 0.0f;
    int valid_samples = 0;
    
    for (int i = 0; i < num_samples; i++) {
        int adc_value = 0;
        if (adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value) == ESP_OK) {
            float voltage = ((float)adc_value / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
            float ac_voltage = fabsf(voltage - bias_voltage);
            float current = ac_voltage * amps_per_volt;
            
            if (current >= 0.0f && current < MAX_CURRENT_AMPS) {
                total += current;
                valid_samples++;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    
    if (valid_samples > 0) {
        float avg_current = total / valid_samples;
        
        if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
            detected_load_amps = avg_current;
            xSemaphoreGive(calibration_mutex);
        }
        
        ESP_LOGI(TAG, "Detected load: %.3f A (from %d samples)", avg_current, valid_samples);
        
        // Process for auto-calibration
        process_current_for_auto_calibration(avg_current);
    } else {
        ESP_LOGW(TAG, "Failed to detect valid load current");
    }
}

void calibrate_with_known_load(float known_amps) {
    ESP_LOGI(TAG, "Calibrating with known load: %.3f A", known_amps);
    
    if (known_amps <= 0.0f || known_amps > MAX_CURRENT_AMPS) {
        ESP_LOGE(TAG, "Invalid known current: %.3f A", known_amps);
        return;
    }
    
    // Take multiple ADC readings
    const int num_samples = 50;
    float voltage_sum = 0.0f;
    int valid_samples = 0;
    
    for (int i = 0; i < num_samples; i++) {
        int adc_value = 0;
        if (adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value) == ESP_OK) {
            float voltage = ((float)adc_value / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
            float ac_voltage = fabsf(voltage - bias_voltage);
            
            if (ac_voltage > 0.001f) { // Avoid near-zero readings
                voltage_sum += ac_voltage;
                valid_samples++;
            }
        }
        vTaskDelay(pdMS_TO_TICKS(50));
    }
    
    if (valid_samples > 10) {
        float avg_voltage = voltage_sum / valid_samples;
        float new_scale = known_amps / avg_voltage;
        
        if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
            amps_per_volt = new_scale;
            xSemaphoreGive(calibration_mutex);
        }
        
        ESP_LOGI(TAG, "Calibration complete: %.2f A/V (from %.4f V RMS)", new_scale, avg_voltage);
        
#if ENABLE_CALIBRATION_LEARNING
        // Add to learning system as manual calibration
        learn_from_calibration(known_amps, avg_voltage, true);
#endif
        
        last_auto_cal_time = xTaskGetTickCount() * portTICK_PERIOD_MS;
    } else {
        ESP_LOGE(TAG, "Calibration failed - insufficient valid samples (%d)", valid_samples);
    }
}

void auto_calibrate_bias_voltage(void) {
    ESP_LOGI(TAG, "Auto-calibrating bias voltage...");
    
    const int num_samples = 100;
    uint32_t voltage_sum = 0;
    int valid_samples = 0;
    
    for (int i = 0; i < num_samples; i++) {
        int adc_value = 0;
        if (adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value) == ESP_OK) {
            voltage_sum += adc_value;
            valid_samples++;
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    
    if (valid_samples > 50) {
        float avg_adc = (float)voltage_sum / valid_samples;
        float new_bias = (avg_adc / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
        
        if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
            bias_voltage = new_bias;
            xSemaphoreGive(calibration_mutex);
        }
        
        ESP_LOGI(TAG, "Bias voltage calibrated to: %.4f V", new_bias);
        consecutive_zero_readings = 0; // Reset zero counter
    } else {
        ESP_LOGE(TAG, "Bias calibration failed - insufficient samples");
    }
}

void print_sct_013_info(void) {
    ESP_LOGI(TAG, "=== SCT-013-000 Configuration ===");
    ESP_LOGI(TAG, "Transformation ratio: %.0f:1", SCT_013_TRANSFORMATION_RATIO);
    ESP_LOGI(TAG, "Burden resistor: %.1f Ω", SCT_013_BURDEN_RESISTOR);
    ESP_LOGI(TAG, "Max secondary current: %.0f mA", SCT_013_MAX_SECONDARY_CURRENT * 1000);
    ESP_LOGI(TAG, "Max secondary voltage: %.3f V RMS", SCT_013_MAX_SECONDARY_VOLTAGE);
    ESP_LOGI(TAG, "Theoretical scale: %.1f A/V", SCT_013_THEORETICAL_SCALE);
    ESP_LOGI(TAG, "Current bias voltage: %.4f V", bias_voltage);
    ESP_LOGI(TAG, "Current scale factor: %.2f A/V", amps_per_volt);
    ESP_LOGI(TAG, "Auto-calibration: %s", auto_calibration_enabled ? "ENABLED" : "DISABLED");
}

float calculate_theoretical_scale_factor(void) {
    return SCT_013_TRANSFORMATION_RATIO / (SCT_013_MAX_SECONDARY_CURRENT * SCT_013_BURDEN_RESISTOR);
}

// Thread-safe parameter access
void set_bias_voltage(float bias_v) {
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        bias_voltage = bias_v;
        xSemaphoreGive(calibration_mutex);
        ESP_LOGI(TAG, "Bias voltage set to: %.4f V", bias_v);
    }
}

float get_bias_voltage(void) {
    float bias = 0.0f;
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        bias = bias_voltage;
        xSemaphoreGive(calibration_mutex);
    }
    return bias;
}

void set_amps_per_volt(float scale) {
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        amps_per_volt = scale;
        xSemaphoreGive(calibration_mutex);
        ESP_LOGI(TAG, "Scale factor set to: %.2f A/V", scale);
    }
}

float get_amps_per_volt(void) {
    float scale = 0.0f;
    if (xSemaphoreTake(calibration_mutex, pdMS_TO_TICKS(100))) {
        scale = amps_per_volt;
        xSemaphoreGive(calibration_mutex);
    }
    return scale;
}

void get_calibration_status(char* status_buffer, size_t buffer_size) {
    if (!status_buffer || buffer_size == 0) return;
    
    snprintf(status_buffer, buffer_size,
             "BIAS_V=%.4f,SCALE=%.2f,AUTO_CAL=%s,AUTO_DET=%s,LOAD=%.3f,LEARNING_PTS=%d",
             get_bias_voltage(),
             get_amps_per_volt(),
             auto_calibration_enabled ? "ON" : "OFF",
             auto_detection_enabled ? "ON" : "OFF",
             get_detected_load_amps(),
#if ENABLE_CALIBRATION_LEARNING
             learning_point_count
#else
             0
#endif
    );
}

void debug_adc_readings(void) {
    ESP_LOGI(TAG, "=== ADC Debug Readings ===");
    
    for (int i = 0; i < 10; i++) {
        int adc_value = 0;
        if (adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value) == ESP_OK) {
            float voltage = ((float)adc_value / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
            float ac_voltage = fabsf(voltage - bias_voltage);
            float current = ac_voltage * amps_per_volt;
            
            ESP_LOGI(TAG, "ADC: %d, V: %.4f, AC: %.4f, I: %.3f A", 
                     adc_value, voltage, ac_voltage, current);
        }
        vTaskDelay(pdMS_TO_TICKS(500));
    }
}

// UDP command handlers with auto-calibration integration
void perform_zero_calibration(int sock, struct sockaddr_in *client_addr) {
    auto_calibrate_bias_voltage();
    
    char response[128];
    snprintf(response, sizeof(response), "ZERO_CAL:SUCCESS,BIAS=%.4f", get_bias_voltage());
    
    sendto(sock, response, strlen(response), 0, 
           (struct sockaddr*)client_addr, sizeof(*client_addr));
    
    ESP_LOGI(TAG, "Zero calibration performed via UDP");
}

void perform_scale_calibration(float known_current, int sock, struct sockaddr_in *client_addr) {
    calibrate_with_known_load(known_current);
    
    char response[128];
    snprintf(response, sizeof(response), "SCALE_CAL:SUCCESS,SCALE=%.2f", get_amps_per_volt());
    
    sendto(sock, response, strlen(response), 0, 
           (struct sockaddr*)client_addr, sizeof(*client_addr));
    
    ESP_LOGI(TAG, "Scale calibration performed via UDP with %.3f A", known_current);
}

void reset_calibration(int sock, struct sockaddr_in *client_addr) {
    set_bias_voltage(ADC_BIAS_VOLTAGE);
    set_amps_per_volt(SCT_013_THEORETICAL_SCALE);
    
#if ENABLE_CALIBRATION_LEARNING
    reset_learning_data();
#endif
    
    reset_auto_cal_statistics();
    
    char response[128];
    snprintf(response, sizeof(response), "RESET_CAL:SUCCESS,BIAS=%.4f,SCALE=%.2f", 
             get_bias_voltage(), get_amps_per_volt());
    
    sendto(sock, response, strlen(response), 0, 
           (struct sockaddr*)client_addr, sizeof(*client_addr));
    
    ESP_LOGI(TAG, "Calibration reset to defaults via UDP");
}