#ifndef SCT_CALIBRATION_H
#define SCT_CALIBRATION_H

#include <stdbool.h>
#include "lwip/sockets.h"

// Device profile structure for automatic recognition
typedef struct {
    float min_current;
    float max_current;
    float typical_current;
    const char* device_name;
    float confidence_boost;  // How much to boost confidence for this device
} device_profile_t;

// Learning point structure for adaptive calibration
typedef struct {
    float expected_current;
    float measured_voltage;
    uint32_t timestamp;
    float confidence;
    bool auto_generated;  // true if from auto-recognition, false if manual
} calibration_point_t;

// Initialize calibration system
void sct_calibration_init(void);

// Auto-detection and auto-calibration controls
void set_auto_calibration(bool enabled);
void set_auto_detection(bool enabled);
bool get_auto_calibration_enabled(void);
bool get_auto_detection_enabled(void);

// Load detection functions
float get_detected_load_amps(void);
void auto_detect_load_current(void);

// Calibration functions
void calibrate_with_known_load(float known_amps);
void print_sct_013_info(void);

// Advanced calibration functions (for UDP commands)
void perform_zero_calibration(int sock, struct sockaddr_in *client_addr);
void perform_scale_calibration(float known_current, int sock, struct sockaddr_in *client_addr);
void reset_calibration(int sock, struct sockaddr_in *client_addr);

// SCT-013 calculations
float calculate_theoretical_scale_factor(void);

// Parameter getters and setters (thread-safe)
void set_bias_voltage(float bias_v);
float get_bias_voltage(void);
void set_amps_per_volt(float scale);
float get_amps_per_volt(void);

// Status functions
void get_calibration_status(char* status_buffer, size_t buffer_size);

// Debug functions
void debug_adc_readings(void);
void auto_calibrate_bias_voltage(void);

// AUTO-CALIBRATION FUNCTIONS (Fixed signatures)
void auto_calibration_task(void *parameters);  // FIXED: Now takes void* parameter
bool should_auto_calibrate_zero(void);
bool should_auto_calibrate_scale(float current_reading);
void process_current_for_auto_calibration(float current_amps);
void auto_recognize_and_calibrate(float measured_current);

// LEARNING SYSTEM FUNCTIONS
void learn_from_calibration(float expected_current, float measured_voltage, bool manual);
void apply_learned_calibration(void);
void reset_learning_data(void);
int get_learning_point_count(void);

// DEVICE RECOGNITION FUNCTIONS
const device_profile_t* recognize_device(float current_amps);
void add_custom_device_profile(float min_current, float max_current, 
                              float typical_current, const char* name);
void list_known_devices(char* buffer, size_t buffer_size);

// ADVANCED AUTO-CALIBRATION
void continuous_auto_calibration(float current_reading);
void temperature_compensation(float temperature_c);  // If temperature sensor available
void adaptive_threshold_adjustment(void);

// CONFIGURATION FUNCTIONS
void set_auto_cal_sensitivity(float sensitivity);  // 0.0 = conservative, 1.0 = aggressive
float get_auto_cal_sensitivity(void);
void set_learning_rate(float rate);
float get_learning_rate(void);

// STATISTICS AND MONITORING
void get_auto_cal_statistics(char* buffer, size_t buffer_size);
uint32_t get_last_auto_cal_time(void);
uint32_t get_auto_cal_count(void);
void reset_auto_cal_statistics(void);

#endif