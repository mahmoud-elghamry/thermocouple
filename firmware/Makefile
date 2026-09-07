MCU := atmega32
F_CPU := 8000000UL
CC := avr-gcc
OBJCOPY := avr-objcopy
SIZE := avr-size
HOST_CC := cc

# Source lists live in sources/ and are read by this Makefile and by
# build.ps1.  Neither carries its own copy - see sources/README.md (I-022).
read_list = $(shell sed -e 's/\#.*//' -e '/^[[:space:]]*$$/d' sources/$(1).txt)

BASE_SOURCES        := $(call read_list,base)
APP_8CH_SOURCES     := $(call read_list,app_8ch)
BANK_31856_SOURCES  := $(call read_list,bank_max31856)
BANK_6675_SOURCES   := $(call read_list,bank_max6675)
APP_LEGACY_SOURCES  := $(call read_list,app_legacy)
SENSOR_31856_SOURCES := $(call read_list,sensor_max31856)
SENSOR_6675_SOURCES  := $(call read_list,sensor_max6675)
HOST_TEST_SOURCES   := $(call read_list,host_test)

CFLAGS := -std=c11 -Os -Wall -Wextra -Werror -mmcu=$(MCU) -DF_CPU=$(F_CPU) \
	-Iinclude -ffunction-sections -fdata-sections -MMD -MP
LDFLAGS := -mmcu=$(MCU) -Wl,--gc-sections

# The product: the eight-channel board, MAX31856.
TARGET_8CH        := build/thermo_8ch_max31856
# Proteus simulation of the same application on MAX6675 models.
TARGET_8CH_SIM    := build/thermo_8ch_max6675_sim
# The superseded single-channel board, kept because one was fabricated.
TARGET_LEGACY_31856 := build/legacy_1ch_max31856
TARGET_LEGACY_6675  := build/legacy_1ch_max6675

obj = $(patsubst %.c,build/%.o,$(1))
# The simulation needs the Proteus SPI mode, so its bank object is built
# separately from the same source.
SIM_BANK_OBJECTS := $(patsubst %.c,build/sim/%.o,$(BANK_6675_SOURCES))

BASE_OBJECTS         := $(call obj,$(BASE_SOURCES))
APP_8CH_OBJECTS      := $(call obj,$(APP_8CH_SOURCES))
BANK_31856_OBJECTS   := $(call obj,$(BANK_31856_SOURCES))
APP_LEGACY_OBJECTS   := $(call obj,$(APP_LEGACY_SOURCES))
SENSOR_31856_OBJECTS := $(call obj,$(SENSOR_31856_SOURCES))
SENSOR_6675_OBJECTS  := $(call obj,$(SENSOR_6675_SOURCES))

ALL_OBJECTS := $(sort $(BASE_OBJECTS) $(APP_8CH_OBJECTS) \
	$(BANK_31856_OBJECTS) $(APP_LEGACY_OBJECTS) \
	$(SENSOR_31856_OBJECTS) $(SENSOR_6675_OBJECTS) $(SIM_BANK_OBJECTS))
DEPENDENCIES := $(ALL_OBJECTS:.o=.d)

TEST_TARGET := build/test_app_logic

.PHONY: all clean size test

all: $(TARGET_8CH).hex $(TARGET_8CH_SIM).hex \
	$(TARGET_LEGACY_31856).hex $(TARGET_LEGACY_6675).hex size

build/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

build/sim/%.o: src/%.c
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -DHAL_MAX6675_SPI_MODE=MCAL_SPI_MODE_1 -c $< -o $@

%.hex: %.elf
	$(OBJCOPY) -O ihex -R .eeprom $< $@

$(TARGET_8CH).elf: $(BASE_OBJECTS) $(APP_8CH_OBJECTS) $(BANK_31856_OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@

$(TARGET_8CH_SIM).elf: $(BASE_OBJECTS) $(APP_8CH_OBJECTS) $(SIM_BANK_OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@

$(TARGET_LEGACY_31856).elf: $(BASE_OBJECTS) $(APP_LEGACY_OBJECTS) \
	$(SENSOR_31856_OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@

$(TARGET_LEGACY_6675).elf: $(BASE_OBJECTS) $(APP_LEGACY_OBJECTS) \
	$(SENSOR_6675_OBJECTS)
	$(CC) $(LDFLAGS) $^ -o $@

size: $(TARGET_8CH).elf $(TARGET_8CH_SIM).elf \
	$(TARGET_LEGACY_31856).elf $(TARGET_LEGACY_6675).elf
	$(SIZE) -C --mcu=$(MCU) $^

$(TEST_TARGET): tests/test_app_logic.c $(addprefix src/,$(HOST_TEST_SOURCES))
	@mkdir -p $(dir $@)
	$(HOST_CC) -std=c11 -Wall -Wextra -Werror -Iinclude $^ -o $@

test: $(TEST_TARGET)
	./$(TEST_TARGET)

clean:
	rm -rf build

-include $(DEPENDENCIES)
