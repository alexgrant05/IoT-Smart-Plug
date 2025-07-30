#include "udp_receiver.h"
#include "hardware_config.h"
#include "sct_calibration.h"
#include "udp_sender.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "lwip/sockets.h"
#include "string.h"
#include "driver/gpio.h"
#include "math.h"


static const char *TAG = "UDP_RECV";

static bool udp_receiver_running = false;
static int udp_recv_socket = -1;

void udp_receiver_task(void *parameters) {
    udp_receiver_running = true;
    ESP_LOGI(TAG, "UDP receiver task started with auto-calibration support");
    
    // Create socket
    udp_recv_socket = socket(AF_INET, SOCK_DGRAM, 0);
    if (udp_recv_socket < 0) {
        ESP_LOGE(TAG, "Failed to create UDP receive socket");
        udp_receiver_running = false;
        vTaskDelete(NULL);
        return;
    }
    
    // Bind socket
    struct sockaddr_in server_addr = {
        .sin_family = AF_INET,
        .sin_addr.s_addr = INADDR_ANY,
        .sin_port = htons(UDP_RECV_PORT)
    };
    
    if (bind(udp_recv_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        ESP_LOGE(TAG, "Failed to bind UDP receive socket");
        close(udp_recv_socket);
        udp_receiver_running = false;
        vTaskDelete(NULL);
        return;
    }
    
    ESP_LOGI(TAG, "UDP receiver listening on port %d", UDP_RECV_PORT);
    
    char buffer[1024];
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);
    
    while (udp_receiver_running) {
        int recv_len = recvfrom(udp_recv_socket, buffer, sizeof(buffer) - 1, 0,
                               (struct sockaddr*)&client_addr, &client_addr_len);
        
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            ESP_LOGI(TAG, "Received command: %s", buffer);
            
            // Process command with auto-calibration support
            process_udp_command(buffer, udp_recv_socket, &client_addr);
        } else if (recv_len < 0) {
            ESP_LOGW(TAG, "UDP receive error");
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }
    
    close(udp_recv_socket);
    udp_recv_socket = -1;
    ESP_LOGI(TAG, "UDP receiver task ended");
    vTaskDelete(NULL);
}

void process_udp_command(const char* command, int sock, struct sockaddr_in* client_addr) {
    char response[1024];
    memset(response, 0, sizeof(response));
    
    ESP_LOGI(TAG, "Processing command: %s", command);
    
    // === RELAY CONTROL ===
    if (strncmp(command, "RELAY_ON", 8) == 0) {
        gpio_set_level(RELAY_GPIO, 1);
        snprintf(response, sizeof(response), "RELAY_ON:SUCCESS");
        
    } else if (strncmp(command, "RELAY_OFF", 9) == 0) {
        gpio_set_level(RELAY_GPIO, 0);
        snprintf(response, sizeof(response), "RELAY_OFF:SUCCESS");
        
    } else if (strncmp(command, "RELAY_TOGGLE", 12) == 0) {
        int current_state = gpio_get_level(RELAY_GPIO);
        gpio_set_level(RELAY_GPIO, !current_state);
        snprintf(response, sizeof(response), "RELAY_TOGGLE:SUCCESS,STATE=%s", 
                 !current_state ? "ON" : "OFF");
    
    // === AUTO-CALIBRATION COMMANDS ===
    } else if (strncmp(command, "AUTO_CAL_ON", 11) == 0) {
        set_auto_calibration(true);
        snprintf(response, sizeof(response), "AUTO_CAL_ON:SUCCESS");
        
    } else if (strncmp(command, "AUTO_CAL_OFF", 12) == 0) {
        set_auto_calibration(false);
        snprintf(response, sizeof(response), "AUTO_CAL_OFF:SUCCESS");
        
    } else if (strncmp(command, "AUTO_CAL_STATUS", 15) == 0) {
        char auto_cal_stats[256];
        get_auto_cal_statistics(auto_cal_stats, sizeof(auto_cal_stats));
        snprintf(response, sizeof(response), "AUTO_CAL_STATUS:%s", auto_cal_stats);
        
    } else if (strncmp(command, "AUTO_CAL_SENSITIVITY:", 21) == 0) {
        float sensitivity = atof(command + 21);
        if (sensitivity >= 0.0f && sensitivity <= 1.0f) {
            set_auto_cal_sensitivity(sensitivity);
            snprintf(response, sizeof(response), "AUTO_CAL_SENSITIVITY:SUCCESS,VALUE=%.2f", sensitivity);
        } else {
            snprintf(response, sizeof(response), "AUTO_CAL_SENSITIVITY:ERROR,INVALID_RANGE");
        }
        
    } else if (strncmp(command, "AUTO_CAL_LEARNING_RATE:", 23) == 0) {
        float rate = atof(command + 23);
        if (rate >= 0.0f && rate <= 1.0f) {
            set_learning_rate(rate);
            snprintf(response, sizeof(response), "LEARNING_RATE:SUCCESS,VALUE=%.2f", rate);
        } else {
            snprintf(response, sizeof(response), "LEARNING_RATE:ERROR,INVALID_RANGE");
        }
    
    // === DEVICE RECOGNITION ===
#if ENABLE_DEVICE_RECOGNITION
    } else if (strncmp(command, "LIST_DEVICES", 12) == 0) {
        char device_list[512];
        list_known_devices(device_list, sizeof(device_list));
        snprintf(response, sizeof(response), "DEVICE_LIST:%s", device_list);
        
    } else if (strncmp(command, "RECOGNIZE_CURRENT:", 18) == 0) {
        float current = atof(command + 18);
        const device_profile_t* device = recognize_device(current);
        if (device) {
            snprintf(response, sizeof(response), 
                     "DEVICE_RECOGNIZED:NAME=%s,TYPICAL=%.2fA,RANGE=%.2f-%.2fA",
                     device->device_name, device->typical_current,
                     device->min_current, device->max_current);
        } else {
            snprintf(response, sizeof(response), "DEVICE_RECOGNIZED:NONE");
        }
        
    } else if (strncmp(command, "AUTO_RECOGNIZE", 14) == 0) {
        float current = get_detected_load_amps();
        auto_recognize_and_calibrate(current);
        snprintf(response, sizeof(response), "AUTO_RECOGNIZE:PROCESSED,CURRENT=%.3fA", current);
#endif
    
    // === LEARNING SYSTEM ===
#if ENABLE_CALIBRATION_LEARNING
    } else if (strncmp(command, "LEARNING_STATS", 14) == 0) {
        int learning_points = get_learning_point_count();
        float learning_rate = get_learning_rate();
        snprintf(response, sizeof(response), 
                 "LEARNING_STATS:POINTS=%d,RATE=%.2f,MAX_POINTS=%d",
                 learning_points, learning_rate, MAX_LEARNING_POINTS);
        
    } else if (strncmp(command, "RESET_LEARNING", 14) == 0) {
        reset_learning_data();
        snprintf(response, sizeof(response), "RESET_LEARNING:SUCCESS");
        
    } else if (strncmp(command, "APPLY_LEARNING", 14) == 0) {
        apply_learned_calibration();
        snprintf(response, sizeof(response), "APPLY_LEARNING:SUCCESS");
#endif
    
    // === ENHANCED CALIBRATION COMMANDS ===
    } else if (strncmp(command, "ZERO_CAL", 8) == 0) {
        perform_zero_calibration(sock, client_addr);
        return; // Response sent by perform_zero_calibration
        
    } else if (strncmp(command, "SCALE_CAL:", 10) == 0) {
        float known_current = atof(command + 10);
        perform_scale_calibration(known_current, sock, client_addr);
        return; // Response sent by perform_scale_calibration
        
    } else if (strncmp(command, "MANUAL_CAL:", 11) == 0) {
        // Parse bias_voltage,scale_factor
        char* comma = strchr(command + 11, ',');
        if (comma) {
            *comma = '\0';
            float bias_voltage = atof(command + 11);
            float scale_factor = atof(comma + 1);
            
            set_bias_voltage(bias_voltage);
            set_amps_per_volt(scale_factor);
            
            snprintf(response, sizeof(response), 
                     "MANUAL_CAL:SUCCESS,BIAS=%.4f,SCALE=%.2f", bias_voltage, scale_factor);
        } else {
            snprintf(response, sizeof(response), "MANUAL_CAL:ERROR,INVALID_FORMAT");
        }
        
    } else if (strncmp(command, "RESET_CAL", 9) == 0) {
        reset_calibration(sock, client_addr);
        return; // Response sent by reset_calibration
        
    } else if (strncmp(command, "CAL_STATUS", 10) == 0) {
        char cal_status[256];
        get_calibration_status(cal_status, sizeof(cal_status));
        snprintf(response, sizeof(response), "CAL_STATUS:%s", cal_status);
    
    // === AUTO-DETECTION COMMANDS ===
    } else if (strncmp(command, "AUTO_DETECT", 11) == 0) {
        auto_detect_load_current();
        float detected = get_detected_load_amps();
        snprintf(response, sizeof(response), "AUTO_DETECT:SUCCESS,CURRENT=%.3fA", detected);
        
    } else if (strncmp(command, "AUTO_DETECT_ON", 14) == 0) {
        set_auto_detection(true);
        snprintf(response, sizeof(response), "AUTO_DETECT_ON:SUCCESS");
        
    } else if (strncmp(command, "AUTO_DETECT_OFF", 15) == 0) {
        set_auto_detection(false);
        snprintf(response, sizeof(response), "AUTO_DETECT_OFF:SUCCESS");
    
    // === MEASUREMENT AND DIAGNOSTICS ===
    } else if (strncmp(command, "GET_CURRENT", 11) == 0) {
        float current = get_instant_current_reading();
        float detected = get_detected_load_amps();
        snprintf(response, sizeof(response), 
                 "CURRENT:INSTANT=%.3fA,DETECTED=%.3fA,VRMS=%.6fV",
                 current, detected, get_last_measured_vrms());
        
    } else if (strncmp(command, "MEASUREMENT_STATS", 17) == 0) {
        char stats[256];
        get_measurement_statistics(stats, sizeof(stats));
        snprintf(response, sizeof(response), "MEASUREMENT_STATS:%s", stats);
        
    } else if (strncmp(command, "RESET_STATS", 11) == 0) {
        reset_measurement_statistics();
        reset_auto_cal_statistics();
        snprintf(response, sizeof(response), "RESET_STATS:SUCCESS");
        
    } else if (strncmp(command, "BUFFER_ANALYSIS", 15) == 0) {
        char analysis[256];
        analyze_voltage_buffer(analysis, sizeof(analysis));
        snprintf(response, sizeof(response), "BUFFER_ANALYSIS:%s", analysis);
        
    } else if (strncmp(command, "DEBUG_ADC", 9) == 0) {
        debug_adc_readings();
        snprintf(response, sizeof(response), "DEBUG_ADC:COMPLETE,CHECK_SERIAL_OUTPUT");
        
    } else if (strncmp(command, "RECALIBRATE_BIAS", 16) == 0) {
        perform_zero_calibration(sock, client_addr);
        return; // Response sent by perform_zero_calibration
    
    // === SCT-013 INFORMATION ===
    } else if (strncmp(command, "SCT_INFO", 8) == 0) {
        print_sct_013_info();
        float theoretical = calculate_theoretical_scale_factor();
        float current_scale = get_amps_per_volt();
        float current_bias = get_bias_voltage();
        
        snprintf(response, sizeof(response),
                 "SCT_INFO:THEORETICAL=%.1fA/V,CURRENT_SCALE=%.2fA/V,BIAS=%.4fV,BURDEN=%.1fOHM",
                 theoretical, current_scale, current_bias, SCT_013_BURDEN_RESISTOR);
    
    // === SYSTEM CONTROL ===
    } else if (strncmp(command, "SYSTEM_STATUS", 13) == 0) {
        uint32_t uptime = xTaskGetTickCount() * portTICK_PERIOD_MS / 1000;
        bool auto_cal_enabled = get_auto_calibration_enabled();
        bool auto_det_enabled = get_auto_detection_enabled();
        uint32_t auto_cal_count = get_auto_cal_count();
        
        snprintf(response, sizeof(response),
                 "SYSTEM_STATUS:UPTIME=%lus,AUTO_CAL=%s,AUTO_DET=%s,CAL_COUNT=%lu,UDP_RUNNING=%s",
                 uptime,
                 auto_cal_enabled ? "ON" : "OFF",
                 auto_det_enabled ? "ON" : "OFF",
                 auto_cal_count,
                 is_udp_sender_running() ? "YES" : "NO");
                 
    } else if (strncmp(command, "PING", 4) == 0) {
        snprintf(response, sizeof(response), "PONG:ESP32_READY,AUTO_CAL_ENABLED");
        
    } else if (strncmp(command, "RESTART", 7) == 0) {
        snprintf(response, sizeof(response), "RESTART:ACKNOWLEDGED");
        // Send response first, then restart
        sendto(sock, response, strlen(response), 0, 
               (struct sockaddr*)client_addr, sizeof(*client_addr));
        vTaskDelay(pdMS_TO_TICKS(1000));
        esp_restart();
        return;
    
    // === CONFIGURATION COMMANDS ===
    } else if (strncmp(command, "GET_CONFIG", 10) == 0) {
        snprintf(response, sizeof(response),
                 "CONFIG:AUTO_CAL=%s,AUTO_DET=%s,LEARNING=%s,DEVICE_RECOG=%s,SENSITIVITY=%.2f",
                 AUTO_CAL_ENABLED ? "ON" : "OFF",
                 get_auto_detection_enabled() ? "ON" : "OFF",
                 ENABLE_CALIBRATION_LEARNING ? "ON" : "OFF",
                 ENABLE_DEVICE_RECOGNITION ? "ON" : "OFF",
                 get_auto_cal_sensitivity());
                 
    } else if (strncmp(command, "SET_BIAS:", 9) == 0) {
        float bias = atof(command + 9);
        if (bias >= 0.1f && bias <= 3.0f) {
            set_bias_voltage(bias);
            snprintf(response, sizeof(response), "SET_BIAS:SUCCESS,VALUE=%.4f", bias);
        } else {
            snprintf(response, sizeof(response), "SET_BIAS:ERROR,INVALID_RANGE");
        }
        
    } else if (strncmp(command, "SET_SCALE:", 10) == 0) {
        float scale = atof(command + 10);
        if (scale >= 1.0f && scale <= 1000.0f) {
            set_amps_per_volt(scale);
            snprintf(response, sizeof(response), "SET_SCALE:SUCCESS,VALUE=%.2f", scale);
        } else {
            snprintf(response, sizeof(response), "SET_SCALE:ERROR,INVALID_RANGE");
        }
    
    // === LEGACY COMMANDS (for backward compatibility) ===
    } else if (strncmp(command, "CALIBRATE:", 10) == 0) {
        float known_current = atof(command + 10);
        calibrate_with_known_load(known_current);
        snprintf(response, sizeof(response), "CALIBRATE:SUCCESS,SCALE=%.2f", get_amps_per_volt());
        
    } else if (strncmp(command, "CAL_KNOWN:", 10) == 0) {
        float known_current = atof(command + 10);
        calibrate_with_known_load(known_current);
        snprintf(response, sizeof(response), "CAL_KNOWN:SUCCESS,SCALE=%.2f", get_amps_per_volt());
    
    // === HELP COMMAND ===
    } else if (strncmp(command, "HELP", 4) == 0) {
        snprintf(response, sizeof(response),
                 "HELP:Commands available - RELAY_ON/OFF/TOGGLE, AUTO_CAL_ON/OFF, AUTO_DETECT, "
                 "ZERO_CAL, SCALE_CAL:X, MANUAL_CAL:bias,scale, GET_CURRENT, SCT_INFO, "
                 "SYSTEM_STATUS, LIST_DEVICES, LEARNING_STATS, PING, HELP");
    
    // === UNKNOWN COMMAND ===
    } else {
        ESP_LOGW(TAG, "Unknown command: %s", command);
        snprintf(response, sizeof(response), "ERROR:UNKNOWN_COMMAND:%s", command);
    }
    
    // Send response
    if (strlen(response) > 0) {
        int sent = sendto(sock, response, strlen(response), 0, 
                         (struct sockaddr*)client_addr, sizeof(*client_addr));
        
        if (sent > 0) {
            ESP_LOGI(TAG, "Response sent: %s", response);
        } else {
            ESP_LOGW(TAG, "Failed to send response");
        }
    }
}

void start_udp_receiver(void) {
    if (udp_receiver_running) {
        ESP_LOGW(TAG, "UDP receiver already running");
        return;
    }
    
    BaseType_t result = xTaskCreate(
        udp_receiver_task,
        "udp_receiver",
        8192,  // Increased stack size for enhanced commands
        NULL,
        4,     // Priority
        NULL
    );
    
    if (result != pdPASS) {
        ESP_LOGE(TAG, "Failed to create UDP receiver task");
    } else {
        ESP_LOGI(TAG, "UDP receiver task created successfully");
    }
}

void stop_udp_receiver(void) {
    if (udp_receiver_running) {
        udp_receiver_running = false;
        ESP_LOGI(TAG, "Stopping UDP receiver");
        
        if (udp_recv_socket >= 0) {
            close(udp_recv_socket);
            udp_recv_socket = -1;
        }
    }
}

bool is_udp_receiver_running(void) {
    return udp_receiver_running;
}