#include "relay.h"
#include "driver/gpio.h"
#include "esp_log.h"
#include "hardware_config.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *TAG = "RELAY";
static bool relay_state = false;
static bool relay_initialized = false;

void relay_init(void) {
    ESP_LOGI(TAG, "Initializing relay on GPIO %d...", RELAY_GPIO);
    
    gpio_config_t io_conf = {
        .pin_bit_mask = 1ULL << RELAY_GPIO,
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE
    };
    
    esp_err_t ret = gpio_config(&io_conf);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to configure relay GPIO: %s", esp_err_to_name(ret));
        return;
    }
    
    // Set initial state to OFF
    gpio_set_level(RELAY_GPIO, 0);
    relay_state = false;
    relay_initialized = true;
    
    ESP_LOGI(TAG, "Relay initialized successfully on GPIO %d, starting OFF", RELAY_GPIO);
    
    // Test the relay briefly
    ESP_LOGI(TAG, "Testing relay...");
    vTaskDelay(pdMS_TO_TICKS(100));
    gpio_set_level(RELAY_GPIO, 1);
    vTaskDelay(pdMS_TO_TICKS(200));
    gpio_set_level(RELAY_GPIO, 0);
    ESP_LOGI(TAG, "Relay test complete");
}

void relay_toggle(void) {
    if (!relay_initialized) {
        ESP_LOGE(TAG, "Relay not initialized - cannot toggle");
        return;
    }
    
    relay_state = !relay_state;
    int gpio_level = relay_state ? 1 : 0;
    
    ESP_LOGI(TAG, "Toggling relay to %s (GPIO level: %d)", 
             relay_state ? "ON" : "OFF", gpio_level);
    
    esp_err_t ret = gpio_set_level(RELAY_GPIO, gpio_level);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set relay GPIO level: %s", esp_err_to_name(ret));
        return;
    }
    
    // Verify the state was set
    int actual_level = gpio_get_level(RELAY_GPIO);
    if (actual_level == gpio_level) {
        ESP_LOGI(TAG, "Relay successfully toggled to %s", relay_state ? "ON" : "OFF");
    } else {
        ESP_LOGE(TAG, "Relay toggle failed - expected %d, got %d", gpio_level, actual_level);
    }
}

bool relay_get_state(void) {
    return relay_state;
}

void relay_set_state(bool state) {
    if (!relay_initialized) {
        ESP_LOGE(TAG, "Relay not initialized - cannot set state");
        return;
    }
    
    relay_state = state;
    int gpio_level = state ? 1 : 0;
    
    ESP_LOGI(TAG, "Setting relay to %s", state ? "ON" : "OFF");
    gpio_set_level(RELAY_GPIO, gpio_level);
}