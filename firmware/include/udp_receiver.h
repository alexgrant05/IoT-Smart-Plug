#ifndef UDP_RECEIVER_H
#define UDP_RECEIVER_H

#include "lwip/sockets.h"

// Main UDP receiver functions
void udp_receiver_task(void *parameters);
void start_udp_receiver(void);
void stop_udp_receiver(void);
bool is_udp_receiver_running(void);

// Command processing
void process_udp_command(const char* command, int sock, struct sockaddr_in* client_addr);

#endif