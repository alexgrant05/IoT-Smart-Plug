#include "wifi.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_mac.h"
#include "nvs_flash.h"
#include <string.h>
#include "freertos/event_groups.h"

#define TAG "WIFI"

static esp_netif_t *sta_netif = NULL;
static esp_netif_t *ap_netif = NULL;
static EventGroupHandle_t wifi_event_group;
static bool ap_running = false;
static bool wifi_initialized = false;

#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT BIT1

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        ESP_LOGI(TAG, "STA started, attempting connection...");
        esp_wifi_connect();
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "WiFi connected! Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
        
        // Disable power saving after connection
        esp_wifi_set_ps(WIFI_PS_NONE);
        ESP_LOGI(TAG, "Disabled WiFi power saving");
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_event_sta_disconnected_t* event = (wifi_event_sta_disconnected_t*) event_data;
        ESP_LOGW(TAG, "Disconnected from WiFi (reason: %d)", event->reason);
        xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
        xEventGroupSetBits(wifi_event_group, WIFI_FAIL_BIT);
        
        // Retry connection with exponential backoff
        static int retry_count = 0;
        int delay_ms = (retry_count < 5) ? (1000 * (1 << retry_count)) : 30000;
        retry_count++;
        
        vTaskDelay(pdMS_TO_TICKS(delay_ms));
        esp_wifi_connect();
        ESP_LOGI(TAG, "Attempting to reconnect (retry %d, delay %dms)...", retry_count, delay_ms);
        
        // Reset retry counter on successful connection
        if (retry_count > 10) retry_count = 0;
        
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_START) {
        ESP_LOGI(TAG, "AP started successfully");
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STOP) {
        ESP_LOGI(TAG, "AP stopped");
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_AP_STACONNECTED) {
        wifi_event_ap_staconnected_t* event = (wifi_event_ap_staconnected_t*) event_data;
        ESP_LOGI(TAG, "Station connected to AP, MAC: %02x:%02x:%02x:%02x:%02x:%02x", 
                 event->mac[0], event->mac[1], event->mac[2], 
                 event->mac[3], event->mac[4], event->mac[5]);
    }
}

void wifi_init_framework(void) {
    if (wifi_initialized) {
        ESP_LOGW(TAG, "WiFi already initialized");
        return;
    }

    // Initialize NVS (Non-Volatile Storage)
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    ESP_LOGI(TAG, "NVS initialized");

    // Initialize network interface and event loop
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    ESP_LOGI(TAG, "Network interface initialized");
    
    // Create event group for Wi-Fi status tracking
    wifi_event_group = xEventGroupCreate();
    if (wifi_event_group == NULL) {
        ESP_LOGE(TAG, "Failed to create event group");
        return;
    }

    // Register event handlers
    ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL));
    ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL));
    ESP_LOGI(TAG, "Event handlers registered");

    // Create network interfaces
    sta_netif = esp_netif_create_default_wifi_sta();
    ap_netif = esp_netif_create_default_wifi_ap();
    
    if (!sta_netif || !ap_netif) {
        ESP_LOGE(TAG, "Failed to create network interfaces");
        return;
    }
    ESP_LOGI(TAG, "Network interfaces created");

    // Initialize Wi-Fi with default config
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    ESP_LOGI(TAG, "WiFi driver initialized");
    
    // Set storage to FLASH to persist credentials
    ESP_ERROR_CHECK(esp_wifi_set_storage(WIFI_STORAGE_FLASH));
    
    // Start with STA mode
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    ESP_LOGI(TAG, "WiFi started in STA mode");
    
    // Configure power settings
    ESP_ERROR_CHECK(esp_wifi_set_max_tx_power(84)); // 21dBm
    esp_wifi_set_ps(WIFI_PS_NONE); // Disable power saving initially
    
    wifi_initialized = true;
    ESP_LOGI(TAG, "Wi-Fi framework initialization complete");
}

void start_fallback_ap(void) {
    if (ap_running) {
        ESP_LOGW(TAG, "AP already running");
        return;
    }

    ESP_LOGI(TAG, "Starting fallback AP...");

    // Stop current WiFi and switch to APSTA mode
    esp_wifi_stop();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_APSTA));

    wifi_config_t ap_config = {
        .ap = {
            .ssid = "ESP32_SETUP",
            .ssid_len = strlen("ESP32_SETUP"),
            .password = "esp32pass",
            .channel = 1,
            .max_connection = 4,
            .authmode = WIFI_AUTH_WPA_WPA2_PSK,
            .pmf_cfg = {
                .required = false
            }
        }
    };

    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &ap_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ap_running = true;
    ESP_LOGI(TAG, "Fallback AP 'ESP32_SETUP' started");
    ESP_LOGI(TAG, "AP IP: 192.168.4.1, Password: esp32pass");
}

void stop_fallback_ap(void) {
    if (!ap_running) {
        ESP_LOGW(TAG, "AP not running");
        return;
    }

    ESP_LOGI(TAG, "Stopping fallback AP...");
    
    esp_wifi_stop();
    vTaskDelay(pdMS_TO_TICKS(100));
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ap_running = false;
    ESP_LOGI(TAG, "AP stopped, switched to STA mode");
}

bool connect_to_wifi(const char *ssid, const char *password) {
    if (!ssid || strlen(ssid) == 0) {
        ESP_LOGE(TAG, "Invalid SSID");
        return false;
    }

    if (!wifi_initialized) {
        ESP_LOGE(TAG, "WiFi not initialized");
        return false;
    }

    ESP_LOGI(TAG, "Attempting to connect to SSID: %s", ssid);

    // Clear any previous bits
    xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT | WIFI_FAIL_BIT);

    // Disconnect if currently connected
    esp_wifi_disconnect();
    vTaskDelay(pdMS_TO_TICKS(100));

    // Configure STA settings
    wifi_config_t sta_config = {0};
    strncpy((char *)sta_config.sta.ssid, ssid, sizeof(sta_config.sta.ssid) - 1);
    if (password && strlen(password) > 0) {
        strncpy((char *)sta_config.sta.password, password, sizeof(sta_config.sta.password) - 1);
    }
    
    // Set scan and connection parameters
    sta_config.sta.scan_method = WIFI_ALL_CHANNEL_SCAN;  // More thorough scan
    sta_config.sta.sort_method = WIFI_CONNECT_AP_BY_SIGNAL;
    sta_config.sta.threshold.rssi = -127;
    sta_config.sta.threshold.authmode = WIFI_AUTH_OPEN;
    sta_config.sta.pmf_cfg.capable = true;
    sta_config.sta.pmf_cfg.required = false;

    esp_err_t err = esp_wifi_set_config(WIFI_IF_STA, &sta_config);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set WiFi config: %s", esp_err_to_name(err));
        return false;
    }

    // Start connection attempt
    err = esp_wifi_connect();
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start connection: %s", esp_err_to_name(err));
        return false;
    }

    // Wait for connection result (extended timeout)
    ESP_LOGI(TAG, "Waiting for connection (timeout: 45s)...");
    EventBits_t bits = xEventGroupWaitBits(wifi_event_group, 
                                        WIFI_CONNECTED_BIT | WIFI_FAIL_BIT, 
                                        pdFALSE, 
                                        pdFALSE, 
                                        pdMS_TO_TICKS(45000));  // Increased to 45s

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "Successfully connected to %s", ssid);
        return true;
    } else {
        ESP_LOGW(TAG, "Failed to connect to %s (timeout or failure)", ssid);
        return false;
    }
}