#ifndef APP_CONFIG_H
#define APP_CONFIG_H

/* Temperatures are stored in tenths of a degree Celsius. */
#define APP_ALARM_ON_TEMP_X10  1000
#define APP_ALARM_OFF_TEMP_X10  950

/* Safe default for a heater: de-energize the output on any sensor fault.
   Set to 1 only when an energized output is the defined safe state. */
#define APP_ALARM_ON_SENSOR_FAULT 0u

#if APP_ALARM_OFF_TEMP_X10 >= APP_ALARM_ON_TEMP_X10
#error "Alarm OFF temperature must be lower than the ON temperature."
#endif

#if APP_ALARM_ON_SENSOR_FAULT > 1u
#error "APP_ALARM_ON_SENSOR_FAULT must be 0 or 1."
#endif

#endif
