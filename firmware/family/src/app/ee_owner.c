#include "app/ee_owner.h"
#include "mcal/eeprom.h"
#include <string.h>
#define QUEUE_SIZE 32u
static set_store_t store;
static settings_t *active;
static calibration_t *calibration;
static uint8_t settings_slot,cal_slot,done,head,tail,count;
static bool settings_ok,begin_notice,transaction,cal_transaction,cal_saved,io_ok,overflow,bg_fault;
static bool counted,counter_pending,event_pending;
static uint8_t counter_slot,counter_index,event_index,event_slot;
static uint32_t cycles;
static events_t ring;
static event_t queue[QUEUE_SIZE];
static ee_op_t operation;
static uint32_t read32(uint16_t address) {
    uint8_t i; uint32_t v=0;
    for(i=0;i<4;i++) v|=(uint32_t)ee_read((uint16_t)(address+i))<<(8*i);
    return v;
}
uint8_t *ee_owner_boot_image(void) { return store.image; }
void ee_owner_init(settings_t *cfg,calibration_t *cal,uint8_t ss,uint8_t cs,bool valid) {
    uint16_t i; uint32_t a,b; bool av,bv;
    active=cfg; calibration=cal; settings_slot=ss; cal_slot=cs; settings_ok=valid;
    done=head=tail=count=0; begin_notice=transaction=cal_transaction=cal_saved=false;
    counted=counter_pending=event_pending=overflow=bg_fault=false; io_ok=true;
    memset(&operation,0,sizeof operation); set_store_init(&store);
    for(i=0;i<512;i++) ((uint8_t *)&ring)[i]=ee_read((uint16_t)(0x840+i));
    a=read32(0x10); b=read32(0x18);
    av=(a^read32(0x14))==UINT32_MAX; bv=(b^read32(0x1C))==UINT32_MAX;
    counter_slot=(uint8_t)(bv && (!av || (b!=a && (uint32_t)(b-a)<0x80000000UL)));
    cycles=av || bv?(counter_slot?b:a):0;
}
bool ee_owner_busy(void) { return transaction; }
bool ee_owner_protection_change(void) { return store.protection_change; }
bool ee_owner_settings_valid(void) { return settings_ok; }
bool ee_owner_cal_saved(void) { return cal_saved; }
bool ee_owner_take_begin(void) { bool b=begin_notice; begin_notice=false; return b; }
uint8_t ee_owner_take_done(void) { uint8_t d=done; done=0; return d; }
fault_code_t ee_owner_fault(void) {
    return overflow?FC_G04_INTERNAL:store.fault!=FC_NONE?store.fault:bg_fault?FC_G13_SAVE_FAIL_INFO:FC_NONE;
}
uint32_t ee_owner_cycles(void) { return cycles; }
static bool background_busy(void) { return counter_pending || event_pending; }
res_t ee_owner_settings(const settings_t *candidate) {
    res_t r;
    if(transaction || background_busy() || !ee_ready()) return RES_BUSY;
    if(!active) return RES_ERR_RANGE;
    r=set_commit_with_cal(&store,candidate,settings_ok?active:NULL,settings_slot,calibration,cal_slot);
    if(r==RES_OK) { transaction=begin_notice=true; cal_transaction=false; io_ok=true; operation.kind=EE_NONE; }
    return r;
}
res_t ee_owner_calibration(const calibration_t *candidate) {
    res_t r;
    if(transaction || background_busy() || !ee_ready()) return RES_BUSY;
    if(!calibration || !candidate || candidate->bank_count!=calibration->bank_count) return RES_ERR_RANGE;
    r=cal_commit(&store,candidate,calibration->sequence,cal_slot);
    if(r==RES_OK) { transaction=begin_notice=cal_transaction=true; cal_saved=false; io_ok=true; operation.kind=EE_NONE; }
    return r;
}
bool ee_owner_log(const event_t *event) {
    if(!event || count==QUEUE_SIZE) { overflow=true; return false; }
    queue[head]=*event; queue[head].power_cycles=(uint16_t)(cycles+(counted?0u:1u));
    head=(uint8_t)((head+1u)%QUEUE_SIZE); ++count; return true;
}
void ee_owner_validated_scan(fault_code_t reset_code,uint32_t uptime) {
    event_t e;
    if(counted) return;
    counted=true; ++cycles; counter_slot^=1; counter_index=0; counter_pending=true;
    memset(&e,0,sizeof e); e.type=EV_POWER_UP; e.code=reset_code; e.uptime_s=uptime;
    (void)ee_owner_log(&e);
}
static void publish(void) {
    /* A wrap can verify calibration before the settings record fails. Publish
     * that verified invalidation even on failure; retries must use its slot. */
    if(store.calibration_slot_known && store.calibration_active_slot!=cal_slot && !cal_transaction) {
        if(cal_unpack(store.wrap_cal_image,calibration->bank_count,calibration)!=RES_OK) overflow=true;
        else cal_slot=store.calibration_active_slot;
    }
    if(store.phase!=STORE_DONE) return;
    if(cal_transaction) {
        if(cal_unpack(store.image,calibration->bank_count,calibration)!=RES_OK) { overflow=true; return; }
        cal_slot=store.active_slot; cal_saved=true; done=2;
    } else {
        if(set_unpack(store.image,active->board_type,active->channel_count,active)!=RES_OK) { overflow=true; return; }
        settings_slot=store.active_slot; settings_ok=true; done=1;
    }
}
void ee_owner_step(void) {
    uint8_t value=0; res_t r;
    if(!ee_ready()) return;
    if(transaction) {
        if(operation.kind==EE_READ) value=ee_read(operation.address);
        set_store_step(&store,true,io_ok,value,&operation); io_ok=true;
        if(operation.kind==EE_WRITE) io_ok=ee_write_byte(operation.address,operation.value)==RES_OK;
        if(store.phase==STORE_DONE || store.phase==STORE_FAILED) {
            publish(); transaction=false;
        }
        return;
    }
    if(counter_pending) {
        uint32_t v=counter_index<4?cycles:~cycles;
        r=ee_write_byte((uint16_t)(0x10+8*counter_slot+counter_index),(uint8_t)(v>>(8*(counter_index%4))));
        if(r==RES_OK) { bg_fault=false; if(++counter_index==8) counter_pending=false; }
        else bg_fault=true;
        return;
    }
    if(!event_pending && count) {
        int slot=ev_log(&ring,&queue[tail]);
        if(slot<0) { overflow=true; return; }
        event_slot=(uint8_t)slot; event_index=0; event_pending=true;
        tail=(uint8_t)((tail+1u)%QUEUE_SIZE); --count;
    }
    if(event_pending) {
        r=ee_write_byte((uint16_t)(0x840+16*event_slot+event_index),ring.slot[event_slot][event_index]);
        if(r==RES_OK) { bg_fault=false; if(++event_index==16) event_pending=false; }
        else bg_fault=true;
    }
}
res_t ee_owner_scratch(uint16_t address,uint8_t value) {
    if(address<0xF00 || address>=0x1000) return RES_ERR_RANGE;
    if(transaction || background_busy() || count || !ee_ready()) return RES_BUSY;
    return ee_write_byte(address,value);
}
