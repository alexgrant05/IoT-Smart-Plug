#ifndef RELAY_H
#define RELAY_H

#include <stdbool.h>

void relay_init(void);
void relay_toggle(void);
bool relay_get_state(void);
void relay_set_state(bool state);

#endif