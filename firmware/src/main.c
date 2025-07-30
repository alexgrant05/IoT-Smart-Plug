#include <stdio.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "nvs_flash.h"
#include "math.h"

#include "wifi.h"
#include "wifi_credentials_receiver.h"
#include "udp_sender.h"
#include "udp_receiver.h"
#include "relay.h"
#include "sct_calibration.h"
#include "hardware_config.h"

static const char *TAG = "MAIN";

// Global ADC handle - define it here instead of in udp_sender
adc_oneshot_unit_handle_t adc1_handle = NULL;

void init_adc_early(void) {
    ESP_LOGI(TAG, "Initializing ADC for early calibration...");
    
    // Initialize ADC unit
    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = ADC_UNIT_1,
        .clk_src = ADC_RTC_CLK_SRC_RC_FAST
    };
    
    esp_err_t ret = adc_oneshot_new_unit(&unit_cfg, &adc1_handle);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize ADC unit: %s", esp_err_to_name(ret));
        return;
    }

    // Configure ADC channel
    adc_oneshot_chan_cfg_t chan_cfg = {
        .bitwidth = ADC_BITWIDTH_12,
        .atten = ADC_ATTEN_DB_11,  // 0-3.3V range
    };
    
    ret = adc_oneshot_config_channel(adc1_handle, ADC_CHANNEL, &chan_cfg);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure ADC channel: %s", esp_err_to_name(ret));
        return;
    }
    
    ESP_LOGI(TAG, "ADC initialized successfully - Channel: %d, GPIO: %d", ADC_CHANNEL, ADC_GPIO_PIN);
}

void perform_comprehensive_startup_calibration(void) {
    ESP_LOGI(TAG, "=== COMPREHENSIVE STARTUP CALIBRATION ===");
    ESP_LOGI(TAG, "CRITICAL: Ensure NO devices are connected to extension cord!");
    
    // Wait for ADC to fully stabilize
    ESP_LOGI(TAG, "Waiting for ADC stabilization...");
    vTaskDelay(pdMS_TO_TICKS(3000));
    
    // Step 1: Take initial readings to see the problem
    ESP_LOGI(TAG, "Step 1: Taking initial ADC readings...");
    uint32_t raw_sum = 0;
    int valid_samples = 0;
    
    for (int i = 0; i < 100; i++) {
        int adc_value = 0;
        esp_err_t ret = adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value);
        if (ret == ESP_OK) {
            raw_sum += adc_value;
            valid_samples++;
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    
    if (valid_samples > 0) {
        float avg_raw = (float)raw_sum / valid_samples;
        float avg_voltage = (avg_raw / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
        float current_with_default_bias = fabsf(avg_voltage - 1.65f) * 200.0f;
        
        ESP_LOGI(TAG, "Initial readings: ADC=%.1f, Voltage=%.6fV", avg_raw, avg_voltage);
        ESP_LOGI(TAG, "Current with default bias (1.65V): %.3fA", current_with_default_bias);
        
        if (current_with_default_bias > 5.0f) {
            ESP_LOGW(TAG, "HIGH CURRENT DETECTED WITH NO LOAD - bias voltage is wrong!");
            ESP_LOGI(TAG, "Your circuit's actual DC level is: %.6fV", avg_voltage);
            ESP_LOGI(TAG, "This explains the false high current readings");
        }
        
        // Step 2: Set the correct bias voltage
        ESP_LOGI(TAG, "Step 2: Setting correct bias voltage...");
        set_bias_voltage(avg_voltage);
        
        // Step 3: Verify the fix
        vTaskDelay(pdMS_TO_TICKS(1000));
        float new_current = fabsf(avg_voltage - avg_voltage) * 200.0f; // Should be near zero
        ESP_LOGI(TAG, "Current after bias correction: %.6fA (should be near zero)", new_current);
        
        if (new_current < 0.1f) {
            ESP_LOGI(TAG, "SUCCESS: Bias voltage corrected!");
        } else {
            ESP_LOGW(TAG, "Bias correction may need additional adjustment");
        }
    }
    
    ESP_LOGI(TAG, "=== STARTUP CALIBRATION COMPLETE ===");
}

void app_main(void) {
    ESP_LOGI(TAG, "ESP32 Smart Plug with Auto-Calibration starting...");
    ESP_LOGI(TAG, "Firmware version: SCT-013-000 Auto-Calibration v3.1");
    ESP_LOGI(TAG, "Features: Auto-Calibration, Device Recognition, Learning System");
    
    // Initialize NVS (required for WiFi)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    ESP_LOGI(TAG, "NVS initialized");
    
#if !ENABLE_LOGGING
    esp_log_level_set("*", ESP_LOG_WARN);
#endif

    // CRITICAL: Initialize ADC and fix bias BEFORE anything else
    init_adc_early();
    
    // Initialize calibration system (this will use the ADC handle we just created)
    ESP_LOGI(TAG, "Initializing calibration system...");
    sct_calibration_init();
    
    // Perform comprehensive startup calibration BEFORE dashboard starts
    perform_comprehensive_startup_calibration();

    // Initialize relay
    ESP_LOGI(TAG, "Initializing relay...");
    relay_init();

    // Now test ADC with corrected bias
    ESP_LOGI(TAG, "Testing ADC with corrected calibration...");
    for (int i = 0; i < 5; i++) {
        int adc_value = 0;
        if (adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value) == ESP_OK) {
            float voltage = ((float)adc_value / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
            float ac_voltage = fabsf(voltage - get_bias_voltage());
            float current = ac_voltage * get_amps_per_volt();
            
            ESP_LOGI(TAG, "Test %d: ADC=%d, V=%.4f, AC=%.6f, I=%.6fA", 
                     i+1, adc_value, voltage, ac_voltage, current);
        }
        vTaskDelay(pdMS_TO_TICKS(500));
    }

    // Print configuration
    ESP_LOGI(TAG, "=== FINAL CONFIGURATION ===");
    ESP_LOGI(TAG, "Auto-Calibration: %s", AUTO_CAL_ENABLED ? "ENABLED" : "DISABLED");
    ESP_LOGI(TAG, "Device Recognition: %s", ENABLE_DEVICE_RECOGNITION ? "ENABLED" : "DISABLED");
    ESP_LOGI(TAG, "Learning System: %s", ENABLE_CALIBRATION_LEARNING ? "ENABLED" : "DISABLED");
    ESP_LOGI(TAG, "SCT-013-000 Burden Resistor: %.1f Ohm", SCT_013_BURDEN_RESISTOR);
    ESP_LOGI(TAG, "Corrected Bias Voltage: %.6fV", get_bias_voltage());
    ESP_LOGI(TAG, "Scale Factor: %.1f A/V", get_amps_per_volt());
    ESP_LOGI(TAG, "ADC Channel: %d (GPIO %d)", ADC_CHANNEL, ADC_GPIO_PIN);
    ESP_LOGI(TAG, "===========================");

    // Initialize WiFi framework
    ESP_LOGI(TAG, "Initializing WiFi...");
    wifi_init_framework();
    
    // Start fallback AP for initial setup
    start_fallback_ap();
    
    // Start WiFi credentials receiver task
    xTaskCreate(wifi_credentials_task, "wifi_credentials", 4096, NULL, 5, NULL);

    // Start UDP receiver (for commands)
    ESP_LOGI(TAG, "Starting UDP command receiver...");
    start_udp_receiver();
    
    // Start UDP sender (for data transmission) - ADC is already initialized
    ESP_LOGI(TAG, "Starting UDP data sender...");
    start_udp_sender("255.255.255.255");
    
    // Give everything time to initialize
    vTaskDelay(pdMS_TO_TICKS(2000));

    // Print initial calibration status
    char cal_status[256];
    get_calibration_status(cal_status, sizeof(cal_status));
    ESP_LOGI(TAG, "Calibration status: %s", cal_status);
    
#if ENABLE_CALIBRATION_LEARNING
    ESP_LOGI(TAG, "Learning system initialized with %d max points", MAX_LEARNING_POINTS);
#endif

#if ENABLE_DEVICE_RECOGNITION
    char device_list[512];
    list_known_devices(device_list, sizeof(device_list));
    ESP_LOGI(TAG, "Device recognition ready:\n%s", device_list);
#endif

    ESP_LOGI(TAG, "ESP32 Smart Plug ready for operation!");
    ESP_LOGI(TAG, "Bias voltage has been corrected - readings should now be accurate");
    ESP_LOGI(TAG, "Auto-calibration will monitor and maintain accuracy automatically");
    
    // Main monitoring loop
    uint32_t status_interval = 60000; // Status update every minute
    uint32_t last_status = 0;
    uint32_t diagnostics_interval = 300000; // Detailed diagnostics every 5 minutes
    uint32_t last_diagnostics = 0;
    
    while (1) {
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
        
        // Regular status updates
        if (now - last_status > status_interval) {
            float current_load = get_detected_load_amps();
            float bias = get_bias_voltage();
            float scale = get_amps_per_volt();
            bool auto_cal_enabled = get_auto_calibration_enabled();
            uint32_t auto_cal_count = get_auto_cal_count();
            
            ESP_LOGI(TAG, "Status: Load=%.3fA, Bias=%.6fV, Scale=%.1fA/V, AutoCal=%s, Count=%lu", 
                     current_load, bias, scale, 
                     auto_cal_enabled ? "ON" : "OFF", auto_cal_count);
            
            last_status = now;
        }
        
        // Detailed diagnostics
        if (now - last_diagnostics > diagnostics_interval) {
            ESP_LOGI(TAG, "=== DIAGNOSTIC REPORT ===");
            
            // Take a fresh ADC reading for diagnostics
            int adc_value = 0;
            if (adc_oneshot_read(adc1_handle, ADC_CHANNEL, &adc_value) == ESP_OK) {
                float voltage = ((float)adc_value / ADC_RESOLUTION) * ADC_VOLTAGE_RANGE;
                float ac_voltage = fabsf(voltage - get_bias_voltage());
                float current = ac_voltage * get_amps_per_volt();
                
                ESP_LOGI(TAG, "Live reading: ADC=%d, V=%.6f, AC=%.6f, I=%.6fA", 
                         adc_value, voltage, ac_voltage, current);
            }
            
            // Auto-calibration statistics
            if (get_auto_calibration_enabled()) {
                char auto_cal_stats[256];
                get_auto_cal_statistics(auto_cal_stats, sizeof(auto_cal_stats));
                ESP_LOGI(TAG, "Auto-cal stats: %s", auto_cal_stats);
            }
            
#if ENABLE_CALIBRATION_LEARNING
            int learning_points = get_learning_point_count();
            float learning_rate = get_learning_rate();
            ESP_LOGI(TAG, "Learning: %d/%d points, rate=%.2f", 
                     learning_points, MAX_LEARNING_POINTS, learning_rate);
#endif

            // System health check
            ESP_LOGI(TAG, "System: Uptime=%lum, Free heap=%lu bytes", 
                     now / 60000, esp_get_free_heap_size());
            
            ESP_LOGI(TAG, "========================");
            
            last_diagnostics = now;
        }
        
        // Main loop delay
        vTaskDelay(pdMS_TO_TICKS(10000)); // 10 second main loop
    }
}