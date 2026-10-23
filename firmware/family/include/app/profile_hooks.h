#ifndef FAMILY_PROFILE_HOOKS_H
#define FAMILY_PROFILE_HOOKS_H
#ifdef FAMILY_REGISTER_MODEL
#include <stdint.h>
extern volatile uint8_t profile_measuring,profile_task_kind;
void profile_task_begin(void);
void profile_task_end(void);
#define PROFILE_TASK_BEGIN(k) do { if(profile_measuring) { profile_task_kind=(k); profile_task_begin(); } } while(0)
#define PROFILE_TASK_END() do { if(profile_measuring) profile_task_end(); } while(0)
#else
#define PROFILE_TASK_BEGIN(k) ((void)0)
#define PROFILE_TASK_END() ((void)0)
#endif
#endif
