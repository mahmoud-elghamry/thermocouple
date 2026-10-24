#ifndef APP_CONFIG_H
#define APP_CONFIG_H

/* Temperatures are stored in tenths of a degree Celsius. */

/* ---- Superseded single-channel board (hal/alarm_output.h) ---------------- */
#define APP_ALARM_ON_TEMP_X10  1000
#define APP_ALARM_OFF_TEMP_X10  950

/* Safe default for a heater: de-energize the output on any sensor fault.
   Set to 1 only when an energized output is the defined safe state. */
#define APP_ALARM_ON_SENSOR_FAULT 0u

/* ---- Eight-channel protection unit -------------------------------------- */
/* No temperature constant lives in the application logic; they are all here.
   APP_8CH_DEFAULT_TRIP_TEMP_X10 is only the value offered to an operator who
   is programming a blank unit - it is never used as a working setpoint.  On a
   blank or corrupted EEPROM the unit refuses to permit running at all, because
   there is no safe guess for how hot this engine may get (R-8, I-012). */
#define APP_8CH_DEFAULT_TRIP_TEMP_X10 2000
#define APP_8CH_HYSTERESIS_X10          50
#define APP_8CH_SETPOINT_STEP_X10       10
#define APP_8CH_MIN_SETPOINT_X10         0
#define APP_8CH_MAX_SETPOINT_X10     12000

/* ---- Scan timing and the trip budget (R-3, I-013) ------------------------ */
/* The main loop period, and how many loops between sensor scans.  These two
   numbers are the whole timing budget, so they live together:

     converter staleness  100 ms  MAX31856 continuous mode, 50 Hz filter
     scan latency         456 ms  APP_8CH_LOOP_PERIOD_MS * APP_8CH_SCAN_TICKS
     loop overhead         57 ms  one more pass, LCD writes included
     relay drop-out        10 ms  G5LE-1 release time
     config verification     5 ms  two extra register reads per channel, all
                                    eight, every scan (I-038); at fCPU/16 SPI
                                    each byte clocks in ~16 us regardless of
                                    what answers, so 32 extra bytes is well
                                    under 1 ms - 5 ms keeps a wide margin
     ------------------------------------
     worst case           628 ms  against the 1 s requirement in docs/GOAL.md

   These are calculated, not measured.  Measuring them on hardware is still
   open - see I-013.  They are only valid with an 8 MHz clock: on the factory
   CKSEL default the part runs at 1 MHz and every delay here is eight times
   longer, which blows the budget by four times (I-032, firmware/fuses.md).

   A setpoint save (I-036) is not in this budget: it only runs while an
   operator is in the edit screen committing a value, never while the unit is
   merely watching temperature, so it cannot delay a trip that is already in
   progress. eeprom_update_block plus the mandatory read-back is bounded by
   the ATmega32A's own EEPROM write time (a few ms per changed byte, six
   bytes here) and blocks only the loop iteration that requested it. */
#define APP_8CH_LOOP_PERIOD_MS  50u
#define APP_8CH_SCAN_TICKS       8u
#define APP_8CH_AUTO_PAGE_TICKS 40u
#define APP_8CH_TRIP_BUDGET_MS 1000u
#define APP_8CH_CONFIG_CHECK_MARGIN_MS 5u

/* ---- Sensor plausibility (I-011) ---------------------------------------- */
/* A cylinder body cannot move 50 degC in one 456 ms scan.  Anything that
   does is a converter or wiring fault, not a temperature. */
#define APP_8CH_MAX_STEP_X10 500

/* A reading that has not moved by 0.1 degC in APP_8CH_STUCK_SCANS scans is
   frozen, not stable: the MAX31856 resolves 0.0078 degC and its own noise
   moves the tenths digit.  120 scans is about 55 s.  This threshold has not
   been confirmed against a running engine - see I-011. */
#define APP_8CH_STUCK_MIN_CHANGE_X10 1
#define APP_8CH_STUCK_SCANS        120u

/* ---- Run-permit driver read-back (I-016) -------------------------------- */
/* How many consecutive scans the read-back may disagree with the pin before
   the unit calls the driver faulty.  More than one, so a relay that is still
   moving does not raise a fault. */
#define APP_8CH_DRIVE_FAULT_SCANS 3u

/* ---- Compile-time sanity ------------------------------------------------ */
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

/* The calculated worst case must stay inside the requirement, or the numbers
   in the comment above have drifted from the constants below them. */
#if (APP_8CH_LOOP_PERIOD_MS * (APP_8CH_SCAN_TICKS + 1u)) + 170u + \
    APP_8CH_CONFIG_CHECK_MARGIN_MS > APP_8CH_TRIP_BUDGET_MS
#error "Scan timing no longer fits the trip budget in docs/GOAL.md."
#endif

#if APP_8CH_STUCK_SCANS == 0u || APP_8CH_STUCK_MIN_CHANGE_X10 <= 0
#error "Stuck-sensor detection would be disabled."
#endif

#if APP_8CH_MAX_STEP_X10 <= 0
#error "Rate-of-change detection would be disabled."
#endif

#if APP_8CH_DRIVE_FAULT_SCANS == 0u
#error "Run-permit read-back would be disabled."
#endif

#endif
