#ifndef TEST_FAKE_UI_H
#define TEST_FAKE_UI_H
#include "app/ui.h"
extern settings_t fake_settings, fake_candidate;
extern prot_state_t fake_protection;
extern prot_out_t fake_output;
extern scan_out_t fake_scan;
extern fault_registry_t fake_faults;
extern uint32_t fake_ms;
extern unsigned fake_commits, fake_frames;
extern res_t fake_commit_result;
extern char fake_frame[80];
extern bool fake_repeat;
void fake_reset(bool blank);
void fake_key(key_t key);
void fake_pump(void);
void fake_finish(res_t result);
void fake_ack(ack_reason_t result);
#endif
