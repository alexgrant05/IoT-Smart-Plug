#ifndef WIFI_H
#define WIFI_H

#include <stdbool.h>

void wifi_init_framework(void);
void start_fallback_ap(void);
void stop_fallback_ap(void);
bool connect_to_wifi(const char *ssid, const char *password);

#endif