#include "wifi_credentials_receiver.h"
#include "wifi.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "lwip/sockets.h"
#include <string.h>
#include <stdio.h>

#define TAG "WIFI_SETUP"
#define WIFI_PORT 4567
#define MAX_RETRY_ATTEMPTS 3
#define MAX_SSID_LEN 32
#define MAX_PASSWORD_LEN 64
#define RX_BUFFER_SIZE 256

void wifi_credentials_task(void *arg) {
    start_fallback_ap();
    
    // Give the AP time to fully start
    vTaskDelay(pdMS_TO_TICKS(2000));

    struct sockaddr_in server_addr, client_addr;
    socklen_t client_addr_len = sizeof(client_addr);
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);

    if (sock < 0) {
        ESP_LOGE(TAG, "Failed to create socket");
        vTaskDelete(NULL);
        return;
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(WIFI_PORT);
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);

    // Allow socket reuse
    int reuse = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

    if (bind(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        ESP_LOGE(TAG, "Failed to bind socket on port %d", WIFI_PORT);
        close(sock);
        vTaskDelete(NULL);
        return;
    }

    ESP_LOGI(TAG, "Listening for Wi-Fi credentials on port %d", WIFI_PORT);

    char rx_buffer[RX_BUFFER_SIZE];
    int retry_count = 0;
    
    while (retry_count < MAX_RETRY_ATTEMPTS) {
        // Set receive timeout
        struct timeval timeout;
        timeout.tv_sec = 30;  // 30 second timeout
        timeout.tv_usec = 0;
        setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

        int len = recvfrom(sock, rx_buffer, sizeof(rx_buffer) - 1, 0,
                           (struct sockaddr *)&client_addr, &client_addr_len);
        
        if (len > 0) {
            // Ensure null termination
            if (len >= sizeof(rx_buffer)) {
                len = sizeof(rx_buffer) - 1;
            }
            rx_buffer[len] = '\0';
            
            // Find comma position safely
            char *comma_pos = strchr(rx_buffer, ',');
            int ssid_len = (comma_pos != NULL) ? (int)(comma_pos - rx_buffer) : strlen(rx_buffer);
            
            // Limit SSID length for logging
            if (ssid_len > MAX_SSID_LEN) {
                ssid_len = MAX_SSID_LEN;
            }

            ESP_LOGI(TAG, "Received credentials from %s: %.*s", 
                    inet_ntoa(client_addr.sin_addr), 
                    ssid_len,
                    rx_buffer);
            
            char ssid[MAX_SSID_LEN + 1], password[MAX_PASSWORD_LEN + 1];
            memset(ssid, 0, sizeof(ssid));
            memset(password, 0, sizeof(password));
            
            // Parse credentials safely
            if (comma_pos != NULL) {
                // Copy SSID
                int copy_len = (comma_pos - rx_buffer);
                if (copy_len > MAX_SSID_LEN) {
                    copy_len = MAX_SSID_LEN;
                }
                strncpy(ssid, rx_buffer, copy_len);
                ssid[copy_len] = '\0';
                
                // Copy password
                const char *pass_start = comma_pos + 1;
                int pass_len = strlen(pass_start);
                if (pass_len > MAX_PASSWORD_LEN) {
                    pass_len = MAX_PASSWORD_LEN;
                }
                strncpy(password, pass_start, pass_len);
                password[pass_len] = '\0';
            } else {
                // No comma, treat entire string as SSID with no password
                strncpy(ssid, rx_buffer, MAX_SSID_LEN);
                ssid[MAX_SSID_LEN] = '\0';
                password[0] = '\0';
            }
            
            ESP_LOGI(TAG, "Parsed SSID: '%s', Password: %s", 
                     ssid, (strlen(password) > 0) ? "[hidden]" : "[empty]");
            
            // Send acknowledgment back to client
            const char *ack = "RECEIVED";
            sendto(sock, ack, strlen(ack), 0, 
                   (struct sockaddr *)&client_addr, client_addr_len);
            
            if (strlen(ssid) > 0 && connect_to_wifi(ssid, password)) {
                ESP_LOGI(TAG, "Successfully connected to Wi-Fi!");
                
                // Send success confirmation
                const char *success = "SUCCESS";
                sendto(sock, success, strlen(success), 0, 
                       (struct sockaddr *)&client_addr, client_addr_len);
                
                // Wait a bit for the message to be sent
                vTaskDelay(pdMS_TO_TICKS(1000));
                
                stop_fallback_ap();
                break;
            } else {
                ESP_LOGW(TAG, "Failed to connect with provided credentials (attempt %d/%d)", 
                         retry_count + 1, MAX_RETRY_ATTEMPTS);
                
                // Send failure notification
                const char *failure = "FAILED";
                sendto(sock, failure, strlen(failure), 0, 
                       (struct sockaddr *)&client_addr, client_addr_len);
                
                retry_count++;
            }
        } else if (len == 0) {
            ESP_LOGW(TAG, "Empty packet received");
        } else {
            ESP_LOGW(TAG, "Receive timeout or error occurred");
        }
    }

    if (retry_count >= MAX_RETRY_ATTEMPTS) {
        ESP_LOGE(TAG, "Max retry attempts reached. Keeping AP mode active.");
    }

    close(sock);
    ESP_LOGI(TAG, "Wi-Fi credentials task ending");
    vTaskDelete(NULL);
}