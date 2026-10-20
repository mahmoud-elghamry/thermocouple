# Brief - Lane F1b: event-queue overflow must not lock the machine out

Continuation of your F1 run (same session). Claude reviewed F1: the gates pass and the integration is accepted
except one item.

`src/app/app.c` `log_event`: when `ee_owner_log` fails (RAM queue of 32 full) it raises **G04**. G04 stays active
and is a trip fault, so ACK is refused (R3) until a power cycle. A real burst does this: island power lost ->
every fitted channel's C fault + trip entry + bank faults in one pass, at ~55 ms per EEPROM entry.

The spec now says what to do: `firmware/spec/05-settings-events.md` 7, paragraph **Burst handling**, and the G13
row of `04-protection.md` 9. Implement it: drop the new entry, count `events lost` (expose a getter for service
mode; add it to the service report if that fits in `service.c`), raise G13 (alarm only) and clear it once the
queue has drained and an ACK was accepted; the first-out TRIP entry is enqueued first in a burst.

Add integration tests: island loss with all 24 channels fitted -> after the island returns and a validated scan,
ACK is **accepted** (RUN possible again without power cycle), G13 was raised and cleared, `events lost` > 0, and
the first stored TRIP entry carries the first-out cause. Same write limits as your F1 brief. Same "Done means"
(clean outputs, three commands, all exit 0). Report under 300 words with counts copied from the output.
