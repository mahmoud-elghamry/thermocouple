/* Fault and cause codes. Numeric values = Modbus fault index (07-modbus.md 4.1); meanings and actions =
 * master table 04-protection.md section 9. Never renumber a released code. Owned by Claude. */
#ifndef FAMILY_COMMON_FAULT_CODES_H
#define FAMILY_COMMON_FAULT_CODES_H

typedef enum {
    FC_NONE = 0,
    /* global */
    FC_G01_SETTINGS_INVALID = 1, FC_G02_SAVE_FAIL_PROT = 2, FC_G03_FLASH_CRC = 3, FC_G04_INTERNAL = 4,
    FC_G05_SCAN_DEADLINE = 5, FC_G06_RUN_FEEDBACK = 6, FC_G07_ALARM_FEEDBACK = 7, FC_G08_ENGREF_LOST = 8,
    FC_G09_ENGREF_TEST = 9, FC_G10_CALIBRATION = 10, FC_G11_RESET_WDT = 11, FC_G12_RESET_BOD = 12,
    FC_G13_SAVE_FAIL_INFO = 13, FC_G14_ISLAND_LOST = 14, FC_G15_FUSES = 15,
    /* bank (unit = bank 0..5) */
    FC_B01_ADC_ID = 21, FC_B02_ADC_CRC = 22, FC_B03_ADC_READBACK = 23, FC_B04_ADC_ERROR = 24,
    FC_B05_ADC_STALLED = 25, FC_B06_REF = 26, FC_B07_AVDD = 27, FC_B08_ZERO = 28, FC_B09_GAIN = 29,
    FC_B10_CJ_BOTH = 30, FC_B11_CJ_DIFF = 31, FC_B12_CJ_ONE = 32, FC_B13_SIGNATURE = 33, FC_B14_RTD = 34,
    FC_B15_ADC_RESET = 35,
    /* channel (unit = channel 0..42, or input pin for C03) */
    FC_C01_OPEN = 41, FC_C02_RANGE = 42, FC_C03_COMMON_MODE = 43, FC_C04_RATE_RESERVED = 44,
    FC_C05_STUCK_RESERVED = 45, FC_C06_SHORTED = 46, FC_C07_OVUV = 47, FC_C08_COLD = 48, FC_C09_RTD = 49,
    /* causes, not faults */
    FC_C10_OVER_TRIP = 50, FC_C11_OVER_ALARM = 51
} fault_code_t;

#endif
