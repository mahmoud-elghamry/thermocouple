MCU := atmega32
F_CPU := 8000000UL
TARGET_31856 := build/thermocouple_meter_max31856
TARGET_6675 := build/thermocouple_meter_max6675
CC := avr-gcc
OBJCOPY := avr-objcopy
SIZE := avr-size
HOST_CC := cc

CFLAGS := -std=c11 -Os -Wall -Wextra -Werror -mmcu=$(MCU) -DF_CPU=$(F_CPU) -Iinclude -ffunction-sections -fdata-sections -MMD -MP
LDFLAGS := -mmcu=$(MCU) -Wl,--gc-sections

COMMON_SOURCES := \
	src/mcal/gpio.c \
	src/mcal/spi.c \
	src/mcal/board.c \
	src/hal/lcd.c \
	src/hal/alarm_output.c \
	src/app/app_logic.c \
	src/app/main.c
COMMON_OBJECTS := $(COMMON_SOURCES:src/%.c=build/%.o)
SENSOR_31856_OBJECT := build/hal/temperature_max31856.o
SENSOR_6675_OBJECT := build/hal/temperature_max6675.o
TEST_TARGET := build/test_app_logic
DEPENDENCIES := $(COMMON_OBJECTS:.o=.d) $(SENSOR_31856_OBJECT:.o=.d) $(SENSOR_6675_OBJECT:.o=.d)

.PHONY: all clean size test

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

$(TEST_TARGET): tests/test_app_logic.c src/app/app_logic.c
	mkdir -p $(dir $@)
	$(HOST_CC) -std=c11 -Wall -Wextra -Werror -Iinclude $^ -o $@

test: $(TEST_TARGET)
	./$(TEST_TARGET)

clean:
	rm -rf build

-include $(DEPENDENCIES)
