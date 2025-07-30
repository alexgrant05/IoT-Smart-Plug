#include "udp_sender.h"
#include "hardware_config.h"
#include "sct_calibration.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_adc/adc_oneshot.h"
#include "lwip/sockets.h"
#include "string.h"
#include <math.h>

static const char *TAG = "UDP_SENDER";

// ADC handle is now defined in main.c and declared extern in udp_sender.h

// Global variables
static int udp_socket = -1;
static struct sockaddr_in dest_addr;
static bool udp_sender_running = false;

// RMS calculation state
#define RMS_BUFFER_SIZE 100
static float voltage_buffer[RMS_BUFFER_SIZE];
static int buffer_index = 0;
static bool buffer_filled = false;

// Auto-calibration integration
static uint32_t measurement_count = 0;
static float last_measured_vrms = 0.0f;

// Statistics for monitoring
static uint32_t total_measurements = 0;
static float min_current = 999999.0f;
static float max_current = 0.0f;
static float accumulated_current = 0.0f;

void udp_sender_init(const char* target_ip) {
    ESP_LOGI(TAG, "Initializing UDP sender to %s:%d", target_ip, UDP_SEND_PORT);
    
    // ADC is already initialized in main.c, just verify it exists
    if (adc1_handle == NULL) {
        ESP_LOGE(TAG, "ADC handle is NULL - ADC must be initialized before UDP sender");
        return;
    }
    
    ESP_LOGI(TAG, "Using existing ADC handle");
    
    // Initialize UDP socket
    udp_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (udp_socket < 0) {
        ESP_LOGE(TAG, "Failed to create UDP socket");
        return;
    }
    
    dest_addr.sin_family = AF_INET;
    dest_addr.sin_port = htons(UDP_SEND_PORT);
    inet_pton(AF_INET, target_ip, &dest_addr.sin_addr.s_addr);
    
    ESP_LOGI(TAG, "UDP sender initialized successfully");
    
    // Initialize statistics
    total_measurements = 0;
    min_current = 999999.0f;
    max_current = 0.0f;
    accumulated_current = 0.0f;
    measurement_count = 0;
}

float measure_rms_current(void) {
    // Fill buffer with ADC readings for RMS calculation
    float voltage_sum_squared = 0.0f;
    int valid_samples = 0;
    
    for (int i = 0; i < RMS_BUFFER_SIZE; i++) {
        int adc_value = 0;
        esp_err_t ret = adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value);
        
        if (ret == ESP_OK) {
            // Convert ADC reading to voltage
            float voltage = ((float)adc_value / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
            
            // Remove DC bias to get AC component
            float ac_voltage = voltage - get_bias_voltage();
            
            // Store in buffer for potential analysis
            voltage_buffer[buffer_index] = ac_voltage;
            buffer_index = (buffer_index + 1) % RMS_BUFFER_SIZE;
            
            if (buffer_index == 0) {
                buffer_filled = true;
            }
            
            // Accumulate for RMS
            voltage_sum_squared += ac_voltage * ac_voltage;
            valid_samples++;
        }
        
        // Small delay for proper AC sampling (aim for ~50-60Hz sampling rate)
        vTaskDelay(pdMS_TO_TICKS(2));
    }
    
    if (valid_samples == 0) {
        ESP_LOGW(TAG, "No valid ADC samples obtained");
        return 0.0f;
    }
    
    // Calculate RMS voltage
    float voltage_rms = sqrtf(voltage_sum_squared / valid_samples);
    last_measured_vrms = voltage_rms;
    
    // Convert to current using calibrated scale factor
    float current_amps = voltage_rms * get_amps_per_volt();
    
    // Update statistics
    total_measurements++;
    if (current_amps < min_current) min_current = current_amps;
    if (current_amps > max_current) max_current = current_amps;
    accumulated_current += current_amps;
    measurement_count++;
    
    // Auto-calibration integration - process this measurement
    if (get_auto_calibration_enabled()) {
        process_current_for_auto_calibration(current_amps);
    }
    
    // Periodic auto-detection (every 50 measurements)
    if (get_auto_detection_enabled() && (measurement_count % 50 == 0)) {
        auto_detect_load_current();
    }
    
#if ENABLE_LOGGING
    // Log detailed information every 100 measurements
    if (measurement_count % 100 == 0) {
        float avg_current = accumulated_current / total_measurements;
        ESP_LOGI(TAG, "Stats - Count: %lu, Current: %.3fA, Avg: %.3fA, Min: %.3fA, Max: %.3fA", 
                 total_measurements, current_amps, avg_current, min_current, max_current);
        
        // Auto-calibration status
        if (get_auto_calibration_enabled()) {
            char auto_cal_stats[256];
            get_auto_cal_statistics(auto_cal_stats, sizeof(auto_cal_stats));
            ESP_LOGI(TAG, "Auto-cal: %s", auto_cal_stats);
        }
    }
#endif
    
    return current_amps;
}

float get_last_measured_vrms(void) {
    return last_measured_vrms;
}

void udp_sender_task(void *parameters) {
    udp_sender_running = true;
    ESP_LOGI(TAG, "UDP sender task started with auto-calibration integration");
    
    uint32_t sequence_number = 0;
    
    while (udp_sender_running) {
        // Measure current
        float current_amps = measure_rms_current();
        
        // Get current timestamp
        uint32_t timestamp = xTaskGetTickCount() * portTICK_PERIOD_MS;
        
        // Create enhanced data packet with auto-calibration info
        char data_packet[512];
        char cal_status[128];
        get_calibration_status(cal_status, sizeof(cal_status));
        
        // Include auto-calibration statistics
        char auto_cal_info[128] = "";
        if (get_auto_calibration_enabled()) {
            get_auto_cal_statistics(auto_cal_info, sizeof(auto_cal_info));
        }
        
        int packet_length = snprintf(data_packet, sizeof(data_packet),
            "SEQ=%lu,TIME=%lu,CURRENT=%.6f,VOLTAGE_RMS=%.6f,POWER=%.2f,CAL_STATUS=%s,AUTO_CAL=%s",
            sequence_number,
            timestamp,
            current_amps,
            last_measured_vrms,
            current_amps * 120.0f, // Assuming 120V AC for power calculation
            cal_status,
            auto_cal_info
        );
        
        // Send UDP packet
        int sent_bytes = sendto(udp_socket, data_packet, packet_length, 0,
                               (struct sockaddr*)&dest_addr, sizeof(dest_addr));
        
        if (sent_bytes < 0) {
            ESP_LOGW(TAG, "Failed to send UDP packet");
        } else if (sequence_number % 50 == 0) { // Log every 50th packet
            ESP_LOGI(TAG, "Sent packet %lu: %.3fA, %.4fV RMS", 
                     sequence_number, current_amps, last_measured_vrms);
        }
        
        sequence_number++;
        
        // Wait before next measurement (2 seconds by default)
        vTaskDelay(pdMS_TO_TICKS(2000));
    }
    
    ESP_LOGI(TAG, "UDP sender task ended");
    vTaskDelete(NULL);
}

void start_udp_sender(const char* target_ip) {
    if (udp_sender_running) {
        ESP_LOGW(TAG, "UDP sender already running");
        return;
    }
    
    udp_sender_init(target_ip);
    
    // Create UDP sender task with higher priority for better timing
    BaseType_t result = xTaskCreate(
        udp_sender_task,
        "udp_sender",
        8192,  // Increased stack size for auto-calibration
        NULL,
        5,     // Higher priority
        NULL
    );
    
    if (result != pdPASS) {
        ESP_LOGE(TAG, "Failed to create UDP sender task");
    } else {
        ESP_LOGI(TAG, "UDP sender task created successfully");
    }
}

void stop_udp_sender(void) {
    if (udp_sender_running) {
        udp_sender_running = false;
        ESP_LOGI(TAG, "Stopping UDP sender");
        
        // Close socket
        if (udp_socket >= 0) {
            close(udp_socket);
            udp_socket = -1;
        }
        
        // Clean up ADC
        if (adc1_handle) {
            adc_oneshot_del_unit(adc1_handle);
            adc1_handle = NULL;
        }
    }
}

bool is_udp_sender_running(void) {
    return udp_sender_running;
}

// Enhanced diagnostic functions with auto-calibration integration
void get_measurement_statistics(char* buffer, size_t buffer_size) {
    if (!buffer || buffer_size == 0) return;
    
    float avg_current = (total_measurements > 0) ? accumulated_current / total_measurements : 0.0f;
    
    snprintf(buffer, buffer_size,
             "MEASUREMENTS=%lu,AVG_CURRENT=%.3f,MIN_CURRENT=%.3f,MAX_CURRENT=%.3f,LAST_VRMS=%.6f",
             total_measurements, avg_current, min_current, max_current, last_measured_vrms);
}

void reset_measurement_statistics(void) {
    total_measurements = 0;
    min_current = 999999.0f;
    max_current = 0.0f;
    accumulated_current = 0.0f;
    measurement_count = 0;
    ESP_LOGI(TAG, "Measurement statistics reset");
}

// Advanced diagnostic function for buffer analysis
void analyze_voltage_buffer(char* buffer, size_t buffer_size) {
    if (!buffer || buffer_size == 0 || !buffer_filled) {
        if (buffer && buffer_size > 0) {
            snprintf(buffer, buffer_size, "BUFFER_ANALYSIS=NOT_READY");
        }
        return;
    }
    
    // Calculate buffer statistics
    float sum = 0, sum_squared = 0;
    float min_val = 999999.0f, max_val = -999999.0f;
    
    for (int i = 0; i < RMS_BUFFER_SIZE; i++) {
        float val = voltage_buffer[i];
        sum += val;
        sum_squared += val * val;
        if (val < min_val) min_val = val;
        if (val > max_val) max_val = val;
    }
    
    float mean = sum / RMS_BUFFER_SIZE;
    float variance = (sum_squared / RMS_BUFFER_SIZE) - (mean * mean);
    float std_dev = sqrtf(variance);
    float rms = sqrtf(sum_squared / RMS_BUFFER_SIZE);
    
    snprintf(buffer, buffer_size,
             "BUFFER_ANALYSIS=READY,MEAN=%.6f,STD_DEV=%.6f,RMS=%.6f,MIN=%.6f,MAX=%.6f,VARIANCE=%.8f",
             mean, std_dev, rms, min_val, max_val, variance);
}

// Function to force an auto-calibration check (useful for testing)
void trigger_auto_calibration_check(void) {
    if (get_auto_calibration_enabled()) {
        float current = measure_rms_current();
        ESP_LOGI(TAG, "Manual auto-calibration check triggered with current: %.3fA", current);
        process_current_for_auto_calibration(current);
    } else {
        ESP_LOGW(TAG, "Auto-calibration is disabled");
    }
}

// Function to get current reading without affecting auto-calibration
float get_instant_current_reading(void) {
    int adc_value = 0;
    esp_err_t ret = adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value);
    
    if (ret == ESP_OK) {
        float voltage = ((float)adc_value / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
        float ac_voltage = fabsf(voltage - get_bias_voltage());
        return ac_voltage * get_amps_per_volt();
    }
    
    return 0.0f;
}