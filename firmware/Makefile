MCU := atmega32
F_CPU := 8000000UL
TARGET_31856 := build/thermocouple_meter_max31856
TARGET_6675 := build/thermocouple_meter_max6675
CC := avr-gcc
OBJCOPY := avr-objcopy
SIZE := avr-size

CFLAGS := -std=c11 -Os -Wall -Wextra -Werror -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Iinclude -ffunction-sections -fdata-sections
LDFLAGS := -mmcu=$(MCU) -Wl,--gc-sections

COMMON_SOURCES := \
	src/mcal/gpio.c \
	src/mcal/spi.c \
	src/mcal/board.c \
	src/hal/lcd.c \
	src/hal/alarm_output.c \
	src/app/main.c
COMMON_OBJECTS := $(COMMON_SOURCES:src/%.c=build/%.o)
SENSOR_31856_OBJECT := build/hal/temperature_max31856.o
SENSOR_6675_OBJECT := build/hal/temperature_max6675.o

.PHONY: all clean size

all: $(TARGET_31856).hex $(TARGET_6675).hex size

build/%.o: src/%.c
	mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(TARGET_31856).elf: $(COMMON_OBJECTS) $(SENSOR_31856_OBJECT)
	$(CC) $(LDFLAGS) $^ -o $@

$(TARGET_31856).hex: $(TARGET_31856).elf
	$(OBJCOPY) -O ihex -R .eeprom $< $@

$(TARGET_6675).elf: $(COMMON_OBJECTS) $(SENSOR_6675_OBJECT)
	$(CC) $(LDFLAGS) $^ -o $@

$(TARGET_6675).hex: $(TARGET_6675).elf
	$(OBJCOPY) -O ihex -R .eeprom $< $@

size: $(TARGET_31856).elf $(TARGET_6675).elf
	$(SIZE) -C --mcu=$(MCU) $^

clean:
	rm -rf build
