#include "hal/buttons.h"
#include "mcal/board.h"
#include "mcal/gpio.h"

#include <stdbool.h>
#include <stdint.h>

#define BUTTON_COUNT 5u
#define DEBOUNCE_POLLS 3u

static const mcal_gpio_pin_t *const button_pins[BUTTON_COUNT] = {
    &BOARD_BUTTON_NEXT,
    &BOARD_BUTTON_UP,
    &BOARD_BUTTON_DOWN,
    &BOARD_BUTTON_SET,
    &BOARD_BUTTON_ACK,
};

static const uint8_t button_events[BUTTON_COUNT] = {
    HAL_BUTTON_EVENT_NEXT,
    HAL_BUTTON_EVENT_UP,
    HAL_BUTTON_EVENT_DOWN,
    HAL_BUTTON_EVENT_SET,
    HAL_BUTTON_EVENT_ACK,
};

static uint8_t stable_pressed;
static uint8_t debounce_counts[BUTTON_COUNT];

void hal_buttons_init(void)
{
    uint8_t index;

    stable_pressed = 0u;
    for (index = 0u; index < BUTTON_COUNT; ++index) {
        debounce_counts[index] = 0u;
        mcal_gpio_input(button_pins[index], true);
    }
}

uint8_t hal_buttons_poll(void)
{
    uint8_t index;
    uint8_t events = HAL_BUTTON_EVENT_NONE;

    for (index = 0u; index < BUTTON_COUNT; ++index) {
        uint8_t mask = (uint8_t)(1u << index);
        bool raw_pressed = !mcal_gpio_read(button_pins[index]);
        bool was_pressed = (stable_pressed & mask) != 0u;

        if (raw_pressed == was_pressed) {
            debounce_counts[index] = 0u;
            continue;
        }

        ++debounce_counts[index];
        if (debounce_counts[index] < DEBOUNCE_POLLS) {
            continue;
        }

        debounce_counts[index] = 0u;
        if (raw_pressed) {
            stable_pressed |= mask;
            events |= button_events[index];
        } else {
            stable_pressed &= (uint8_t)~mask;
        }
    }
    return events;
}
