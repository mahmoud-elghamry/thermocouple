#ifndef FAMILY_APP_VIEW_H
#define FAMILY_APP_VIEW_H
#include "app/modbus.h"
void app_view_init(void);
void app_view_result(uint8_t ch,const result_t *r,act_t action);
void app_view_cause(fault_code_t code,uint8_t channel,uint8_t unit);
void app_view_ack(void);
void app_view_step(void);
uint32_t app_uptime_s(void);
#endif
