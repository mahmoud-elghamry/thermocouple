#ifndef FAMILY_ACK_INPUT_H
#define FAMILY_ACK_INPUT_H
#include "app/protection.h"
void ack_input_init(void);
void ack_input_cancel(void); /* boot/trip/settings boundary: release again */
void ack_input_step(prot_in_t *input); /* consumes key queue each pass */
#endif
