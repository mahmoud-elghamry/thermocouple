#ifndef APP_CONFIG_H
#define APP_CONFIG_H

/* Temperatures are stored in tenths of a degree Celsius. */
#define APP_ALARM_ON_TEMP_X10  1000
#define APP_ALARM_OFF_TEMP_X10  950

/* Safe default for a heater: de-energize the output on any sensor fault.
   Set to 1 only when an energized output is the defined safe state. */
#define APP_ALARM_ON_SENSOR_FAULT 0u

/* Eight-channel Proteus defaults.  These live in one configuration header so
   the application logic contains no hidden temperature constants. */
#define APP_8CH_DEFAULT_TRIP_TEMP_X10 2000
#define APP_8CH_HYSTERESIS_X10          50
#define APP_8CH_SETPOINT_STEP_X10       10
#define APP_8CH_MIN_SETPOINT_X10         0
#define APP_8CH_MAX_SETPOINT_X10     12000

#if APP_ALARM_OFF_TEMP_X10 >= APP_ALARM_ON_TEMP_X10
#error "Alarm OFF temperature must be lower than the ON temperature."
#endif

#if APP_ALARM_ON_SENSOR_FAULT > 1u
#error "APP_ALARM_ON_SENSOR_FAULT must be 0 or 1."
#endif

#if APP_8CH_DEFAULT_TRIP_TEMP_X10 < APP_8CH_MIN_SETPOINT_X10 || \
    APP_8CH_DEFAULT_TRIP_TEMP_X10 > APP_8CH_MAX_SETPOINT_X10
#error "Eight-channel default trip temperature is outside the allowed range."
#endif

#if APP_8CH_HYSTERESIS_X10 < 0 || APP_8CH_SETPOINT_STEP_X10 <= 0
#error "Eight-channel hysteresis and setpoint step must be valid."
#endif

#endif
