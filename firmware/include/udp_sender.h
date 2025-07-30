#ifndef UDP_SENDER_H
#define UDP_SENDER_H

#include <stdbool.h>
#include <stddef.h>
#include "esp_adc/adc_oneshot.h"

// Global ADC handle - declared as extern, defined in main.c
extern adc_oneshot_unit_handle_t adc1_handle;

// Initialize UDP sender
void udp_sender_init(const char* target_ip);

// Main sending function (runs as task)
void udp_sender_task(void *parameters);

// Control functions
void start_udp_sender(const char* target_ip);
void stop_udp_sender(void);
bool is_udp_sender_running(void);

// Measurement functions
float measure_rms_current(void);
float get_last_measured_vrms(void);
float get_instant_current_reading(void);

// Diagnostic functions
void get_measurement_statistics(char* buffer, size_t buffer_size);
void reset_measurement_statistics(void);
void analyze_voltage_buffer(char* buffer, size_t buffer_size);
void trigger_auto_calibration_check(void);

#endif