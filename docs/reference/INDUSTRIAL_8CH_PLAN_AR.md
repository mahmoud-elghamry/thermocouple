# خطة تطوير وحدة حماية حرارة صناعية — 8 قنوات Thermocouple

**حالة الوثيقة:** Baseline متطلبات وArchitecture قبل تصميم نسخة الإنتاج  
**آخر تحديث:** 2026-09-03  
**المشروع الحالي:** نموذج قناة واحدة في Proteus/KiCad، وليس منتجًا صناعيًا معتمدًا بعد

## 1. الهدف وحدود هذه الوثيقة

المطلوب تطوير وحدة داخل لوحة تحكم صناعية تقوم بالآتي:

- قراءة 8 حساسات K-Type Thermocouple.
- العمل Standalone أو كوحدة Slave تتصل بلوحة Master.
- عرض القراءات والأعطال، وضبط نقطة الفصل محليًا.
- فصل/منع تشغيل الموتور عند ارتفاع الحرارة أو عطل القياس.
- إعطاء أولوية دائمة للفصل المحلي؛ لا يستطيع أمر تشغيل خارجي تجاوز حالة غير آمنة.
- استقبال 24 VDC من لوحة التحكم.
- توفير خرج تقليدي سهل الدمج، واتصال صناعي ذكي اختياري.

هذه الوثيقة تمنع ضياع القرارات بين رسائل المحادثة. هي **خطة تصميم واختبار** وليست
إقرارًا بأن اللوحة مطابقة لمعيار أو صالحة لوظيفة Safety/SIL قبل تنفيذ الاختبارات
والمراجعات المطلوبة.

## 2. ما نعرفه الآن

| البند | القرار أو المعلومة الحالية | الحالة |
|---|---|---|
| عدد القنوات | 8 Thermocouples | ثابت مبدئيًا |
| النوع | K-Type | يحتاج رقم الموديل والداتا شيت |
| تركيب الطرف | Grounded junction / grounded tip | معلومة حرجة |
| طول الكابل | قد يصل إلى 50 m من الحساس إلى البانل | معلومة حرجة |
| التغذية | 24 VDC من البانل | يلزم تحديد المدى والتذبذب الفعليين |
| أوضاع العمل | Standalone وRemote/Slave | مطلوب |
| القرار الآمن | OFF/TRIP له الأولوية على أي أمر ON | متفق عليه |
| الضبط المحلي | أزرار لضبط Setpoint والتنقل بين القنوات | مطلوب |
| الاتصال | عدة وحدات مع Master داخل بانل غالبًا | مطلوب |
| الخرج الأساسي | إشارة فتح/قفل كلاسيكية | مطلوب |
| الخرج الذكي | مرغوب للتكامل مع VFD/PLC عند الحاجة | مطلوب كخيار |
| البيئة | Oil & Gas / ماكينة صناعية | يلزم تحديد Zone وظروف البانل |

## 3. أهم نتيجة هندسية: Grounded tip مع كابل 50 m

إشارة الـThermocouple صغيرة جدًا وتقاس بالـmillivolt. الطرف الـgrounded موصل
كهربائيًا بغلاف الحساس، وبالتالي قد يحمل جهد أرضي الماكينة، وهذا الجهد قد يختلف
عن أرضي لوحة القياس. ومع 50 m تزيد مساحة التقاط الضوضاء واحتمالات:

- Ground loop بين الماكينة والبانل.
- تجاوز Common-mode range لواجهة القياس.
- التقاط 50 Hz وضوضاء الـVFD والكونتاكتورات.
- ESD/EFT/Surge أو جهد عابر على مدخل حساس دقيق.
- خطأ قراءة أو OV/UV fault أو تلف الواجهة.
- توصيل ثماني نقاط أرضية مختلفة معًا إذا اشتركت القنوات في أرضي Analog واحد.

شركة Analog Devices تنص على أن MAX31856 غير مقصود مباشرة للطرف الـgrounded،
وتوصي عند الاضطرار باستخدامه بعزل تغذيته عن أرضي الحساس وعزل الاتصال الرقمي مع
المتحكم. لذلك لا نعتمد التصميم الآتي للنسخة الميدانية:

```text
8 grounded thermocouples, 50 m -> 8 MAX31856 -> common PCB ground
```

وجود Filter أو Shield أو DRC=0 لا يحل فرق الجهد الأرضي. كذلك نجاح Proteus لا
يحاكي Ground loop أو الكابل أو EMC.

### 3.1 اختيار Architecture القياس

الاختيارات مرتبة حسب الأفضلية المبدئية، والقرار النهائي بعد فحص الحساس والجهاز
الحالي في الموقع.

#### الخيار A — المفضل للمجال الصناعي: تحويل قريب من الحساس إلى 4–20 mA

```text
K-Type sensor
   -> certified head/field temperature transmitter
   -> 4–20 mA loop over 50 m
   -> protected/isolated 8-channel analog input in panel
```

المزايا:

- الـ4–20 mA أنسب بكثير للمسافات الطويلة والضوضاء الصناعية.
- يمكن اكتشاف قطع السلك/خروج التيار عن المدى حسب إعداد الـtransmitter.
- توجد Transmitters صناعية معزولة ومعتمدة للبيئات المطلوبة.
- يقل الجزء الحساس للـmicrovolts إلى مسافة قصيرة عند نقطة القياس.

القيود:

- تكلفة ثمانية Transmitters وتغذيتها وتركيبها.
- يلزم التأكد من مساحة/حرارة/حماية مكان تركيب كل Transmitter.
- في Hazardous Area يجب اختيار Transmitter/Barrier/طريقة تمديد معتمدة للـZone،
  وليس تصميم حل منزلي داخل المنطقة الخطرة.

#### الخيار B — إبقاء الـThermocouples الخام حتى البانل مع عزل القنوات

```text
Each grounded TC
   -> input protection + balanced filter
   -> isolated thermocouple front-end
   -> channel-to-channel / channel-to-system isolation
   -> MCU
```

إذا استخدمنا MAX31856، فالافتراض الآمن هو جزيرة معزولة لكل قناة: تغذية معزولة
وممر SPI معزول، إلا إذا أثبتت دراسة الجهود الأرضية أن مجموعة محددة يمكنها مشاركة
العزل. هذا الحل أكبر وأغلى وأصعب في الـPCB والاختبار، لكنه يبقي الكابلات الحالية.

#### الخيار C — تغيير الحساسات إلى Ungrounded

يمكنه تبسيط واجهة القياس، لكنه قرار Process/Mechanical وليس قرار إلكترونيات فقط.
لا يُنفذ إلا إذا وافق المسؤول عن العملية وتأكدت سرعة الاستجابة والاعتماد الميكانيكي.

#### قرار لا يؤخذ قبل المعاينة

يجب تصوير وقراءة موديل جهاز الحماية التجاري الموجود حاليًا، وموديل الحساس،
وطريقة توصيل الشيلد والأرضي. قد يكون الجهاز الحالي يملك عزل قناة-إلى-قناة، أو
يستخدم Transmitters خارجية، وهذه معلومة تختصر التصميم وتمنع افتراضًا خطأ.

## 4. Architecture النظام المقترح

```text
                         +--------------------------+
8 field sensors -------->| Isolated measurement     |
                         | 8 channels + diagnostics |
                         +------------+-------------+
                                      |
24 VDC -> Protection -> DC/DCs ------>| MCU + watchdog + NVM
                                      |       |
                                      |       +-> Display + buttons
                                      |       +-> Isolated RS-485/Modbus RTU
                                      |       +-> RUN_PERMIT dry contact
                                      |       +-> AUX_ALARM dry contact
                                      |       +-> Optional isolated 4-20mA/0-10V
                                      +-------------------------------
```

يقسم التصميم إلى ست مناطق واضحة:

1. حماية ودخول 24 VDC.
2. واجهات القياس المعزولة.
3. المتحكم والذاكرة والـWatchdog.
4. واجهة المستخدم.
5. الاتصال المعزول.
6. المخارج، مع فصل كهربائي ومسافات واضحة بينها وبين القياس.

## 5. المخارج: ما معنى «يشتغل مع أي حاجة» عمليًا؟

لا يوجد خرج إلكتروني آمن حرفيًا مع **أي فولت وأي تيار**. كل Contact أو Transistor
له حد جهد وتيار ونوع حمل ودرجة عزل. نحقق المرونة بواجهات قياسية منفصلة.

### 5.1 الخرج الأساسي — RUN_PERMIT Dry Contact

يوفر Terminal من نوع Form-C:

```text
COM   NO   NC
```

- الـContact لا يخرج فولت من اللوحة؛ المستخدم يمرر من خلاله فولت دائرة التحكم.
- يستخدم لتغذية مدخل PLC/VFD أو Coil لريلاي Interposing مناسب.
- لا يستخدم لتغذية الموتور مباشرة.
- نختار منطق **Energized-to-run**: في الحالة الصحية يعمل ريلاي السماح ويغلق
  مسار RUN_PERMIT، وعند الحرارة العالية أو Fault أو فقد تغذية اللوحة يسقط الريلاي
  فيمنع التشغيل.
- يوضع على Silkscreen وManual حد الجهد/التيار الحقيقي. النسخة الأولى يفضل أن
  تظل SELV/PELV منخفضة الجهد؛ إذا احتجنا 230 VAC نستخدم Interposing Relay معتمدًا
  خارج اللوحة، أو نعيد تصميم منطقة عزل Mains رسميًا.

### 5.2 خرج ثانٍ — AUX_ALARM Dry Contact

خرج منفصل للإنذار أو إرسال حالة Fault عامة للـPLC. لا يحمل قرار السماح الرئيسي،
حتى يمكن تشخيص Alarm من دون العبث بمسار الحماية.

### 5.3 الاتصال الذكي — Isolated RS-485 / Modbus RTU

هو الاختيار الأساسي لتبادل:

- درجات القنوات الثماني.
- Valid/Fault لكل قناة.
- Setpoints وHysteresis وحالة Latch.
- حالة RUN_PERMIT وسبب الفصل.
- أوامر Master المسموح بها.
- Diagnostics ونسخة Firmware وعدادات Reset/Communication fault.

RS-485 هو الطبقة الكهربائية، وModbus RTU هو البروتوكول. داخل البانل يظل اختيارًا
مفيدًا لأنه Differential، يدعم عدة Slaves، ومألوف في PLC/VFD. توضع مقاومة
Termination فقط عند طرفي الـbus، ويكون لكل Slave عنوان فريد.

### 5.4 خرج Analog اختياري — 4–20 mA أو 0–10 V

يضاف فقط إذا أعطانا المهندس Use case محددًا، مثل إرسال أعلى درجة حرارة أو Speed
Reference للـVFD. يفضل 4–20 mA عند وجود ضوضاء أو مسافة؛ 0–10 V شائع داخل البانل
لكن أكثر تأثرًا بفرق الأرضي. في الحالتين نحتاج عزلًا وحماية ودقة واختبار حمل.

### 5.5 لماذا لا نجعل PWM هو الحل العام؟

PWM/نبضات ليست واجهة عامة لكل VFD أو PLC. بعض المداخل تقبل Frequency input
بحدود جهد وتردد ودورة معينة، وبعضها لا يقبله. لذلك:

- RUN/STOP: Dry contact أو 24 V digital input.
- Speed/reference: 4–20 mA أو 0–10 V إذا مطلوب.
- أوامر وقراءات كاملة: Modbus RTU.
- PWM/Frequency: DNP مبدئيًا، ولا يضاف إلا إذا نص Manual الجهاز المطلوب عليه.

## 6. منطق الأمان والأولوية

### 6.1 قاعدة عامة

```text
أي سبب محلي غير آمن -> RUN_PERMIT = OFF
Master OFF          -> RUN_PERMIT = OFF
Master ON           -> مسموح فقط إذا كل الشروط المحلية آمنة
```

### 6.2 Truth table في Remote mode

| Local state | Master command | النتيجة |
|---|---|---|
| Unsafe/Trip/Fault | ON | OFF — أمر التشغيل مرفوض |
| Unsafe/Trip/Fault | OFF | OFF |
| Safe | OFF | OFF |
| Safe | ON | ON |
| Safe | لا يوجد اتصال | OFF افتراضيًا، ويؤكد المهندس هذه السياسة |

### 6.3 أسباب الفصل المحلي المقترحة

- أي قناة Enabled تجاوزت High-High trip.
- Open/short/OV/UV أو قراءة غير صالحة في قناة الحماية.
- فشل تهيئة أو قراءة واجهة القياس.
- Internal watchdog/reset غير مفسر.
- Brownout أو مشكلة تغذية تمنع وثوق القرار.
- فقد اتصال Master إذا اختير Remote mode وسياسة الموقع هي fail-off.
- زر Emergency/External trip input إن طلبه التصميم النهائي.

### 6.4 Latch وACK

الافتراضي المقترح لوظيفة الحماية:

1. عند تجاوز Trip، يفتح RUN_PERMIT فورًا.
2. يظل Trip latched حتى لو انخفضت الحرارة.
3. لا يقبل ACK/Reset إلا إذا انخفضت كل القنوات تحت Reset threshold واختفت الأعطال.
4. ACK لا يشغل الموتور؛ هو فقط يمسح الـLatch. التشغيل يحتاج أمر تشغيل مستقل.

يجب تأكيد هل الـLatch مطلوب لكل Trip أم لبعض الحالات فقط، وهل لكل قناة Setpoint
مختلف، وهل Trip قناة واحدة يفصل موتورًا واحدًا أم يفصل المجموعة كلها.

## 7. واجهة المستخدم المحلية

لثماني قنوات، شاشة 16x2 ممكنة لكنها محدودة. الاختيارات:

- Prototype: LCD 20x4 أو 16x2 مع صفحات.
- منتج Panel أفضل: Display صناعي واضح أو HMI منفصلة، حسب التكلفة والبيئة.

الأزرار المقترحة:

- `NEXT/CHANNEL`: التنقل بين القنوات.
- `UP` و`DOWN`: تغيير قيمة.
- `SET/ENTER`: اعتماد القيمة.
- `ACK/RESET`: مسح Trip بعد تحقق شروط الأمان.
- مفتاح/Parameter لاختيار LOCAL/REMOTE إن كان مطلوبًا تشغيليًا.

قواعد مهمة:

- لا يسمح بتغيير Setpoint بلا دخول واضح إلى Setup.
- تحفظ الإعدادات مع Version وCRC ونسخة احتياطية/Defaults.
- يوضع حد أدنى وأقصى لكل قيمة.
- يظهر سبب الفصل والقناة، وليس كلمة FAULT عامة فقط.
- أي قناة Disabled تظهر بوضوح وتسجل في Diagnostics.

## 8. اختيار المتحكم

### ATmega32A

يمكنه تنفيذ نسخة ثابتة: 8 قنوات، شاشة وأزرار، خرجان، وModbus RTU إذا أُديرت
الأرجل والذاكرة بعناية. ميزته البساطة والعمل عند 5 V، لكن لديه 2 KB SRAM وUSART
واحد ومساحة توسع محدودة. ومع العزل وواجهات متعددة قد نحتاج Expanders أو Decoder.

### STM32G0 أو متحكم صناعي حديث مماثل

مفضل عندما نريد:

- Diagnostics وسجل أحداث وإعدادات أكثر.
- أكثر من واجهة اتصال أو Bootloader موثوق.
- قنوات/مخارج إضافية مستقبلًا.
- CRC/Timers/DMA وWatchdogs أفضل.
- مساحة كود واختبار أكبر.

عمله عند 3.3 V ليس عيبًا جوهريًا؛ واجهات 24 V وRS-485 وRelay وAnalog تحتاج
Drivers/Isolation في الحالتين. لا نوصل 24 V أو 5 V مباشرة برجل 3.3 V.

### ESP32

أنسب كـMaster/Gateway للـEthernet/Wi-Fi/MQTT، وليس أول اختيار لمسار Trip المحلي.
يمكن أن يجمع بيانات الوحدات عبر Modbus ويعرضها أو يرسلها إلى Server، بينما يظل
الفصل المحلي في وحدة deterministic لا يعتمد على الشبكة أو السحابة.

### قرار المتحكم

لا يثبت قبل اختيار Architecture مدخلات القياس وحصر I/O النهائي. المبدأ:

- Scope ثابت وتكلفة منخفضة: ATmega32A ما زال ممكنًا.
- منتج قابل للتوسع وتشخيص أقوى: STM32G0 هو المرشح المبدئي.

## 9. دخول 24 VDC والطاقة

اللوحة الحالية تستقبل 5 V منظمًا، لذلك لا توصل على 24 V. نسخة 8 قنوات تحتاج:

- Fuse أو resettable protection محسوبًا.
- Reverse-polarity protection.
- TVS مناسبًا لنظام 24 V بعد معرفة مستوى الـsurge المطلوب.
- EMI input filter وتحديد inrush.
- Buck converter صناعي إلى 5 V/3.3 V، وليس AMS1117 من 24 V.
- Brownout detection وPower-good إن أمكن.
- تغذيات معزولة للقنوات/الاتصال حسب Architecture.
- فصل واضح بين Chassis/PE و0 V وAnalog isolated returns.
- قياس استهلاك Worst-case وحرارة المحولات داخل البانل.

يلزم سؤال الشركة: هل 24 V هو SELV/PELV من Power Supply مشتركة؟ ما المدى الفعلي،
والـripple، وهل توجد ملفات Solenoid/Contactor على نفس المصدر؟

## 10. قواعد PCB المبدئية للنسخة الصناعية

### عدد الطبقات

النسخة الحالية طبقتان ومناسبة كنموذج قناة واحدة منخفض الجهد. نسخة 8 قنوات مع
عزل و24 V وRS-485 قد تحتاج 4 طبقات لتحسين return paths والطاقة وتقليل المساحة،
لكن عدد الطبقات لا يقرر قبل رسم حدود العزل والـfloorplan.

تقسيم أولي لأربع طبقات:

1. Top: مكونات وإشارات قصيرة.
2. Inner 1: planes/returns مقسمة فقط حسب حدود العزل المدروسة.
3. Inner 2: power distribution.
4. Bottom: إشارات بطيئة ومكونات مسموحة.

لا نضع Ground plane يعبر isolation barrier. Slots وcreepage وclearance تتحدد
من working voltage، pollution degree، material group، altitude، transient
category والمعيار، لا من رقم محفوظ عام.

### Placement

- مداخل الحساس عند حافة منفصلة وبعيدة عن Relay وDC/DC وClock.
- مسارا T+ وT- متطابقان قدر الإمكان، والفلتر والحماية قرب Connector.
- Cold-junction sensor/front-end قرب نقطة انتقال معدن الـThermocouple إلى Copper.
- RS-485 والحماية قرب موصل الـbus.
- Relay contacts في منطقة منفصلة، ومع Terminal واضح.
- Test points للطاقة والاتصال وكل قناة وTrip chain.
- Connector keying وتسميات تمنع تبديل 24 V مع sensor أو bus.

### EMC والحماية

- Shielded twisted K-type extension cable صحيح النوع والقطبية.
- خطة إنهاء Shield عند دخول البانل/Chassis تُعتمد بعد معرفة تركيب الموقع؛ لا نوصل
  الشيلد عشوائيًا عند الطرفين ونصنع Ground loop.
- Balanced RC filtering لا يفسد Common-mode rejection.
- حماية ESD/EFT/Surge مختارة بحيث لا تضيف leakage/offset يفسد microvolt input.
- Snubber/coil suppression على الأحمال الحثية خارج اللوحة أيضًا.
- لا نسير مسارات Sensor بالتوازي مع موتور/VFD؛ يراعى فصل كابلات القدرة والتحكم.

## 11. Software Architecture المقترح

نحافظ على MCAL/HAL/APP الحالي ونوسعه بدل خلط كل شيء في `main.c`:

```text
APP
  protection state machine
  channel scheduler
  local/remote arbitration
  UI and configuration
  event/diagnostic manager

SERVICES
  Modbus RTU
  NVM with CRC/version
  event log
  self-test

HAL
  8-channel temperature interface
  isolated inputs/front-end driver
  relay/digital/analog outputs
  display/buttons

MCAL
  GPIO / SPI / UART / timers / watchdog / CRC / flash
```

### حالات النظام

```text
POWER_ON_SELF_TEST
INIT
SAFE_READY
RUNNING
TRIPPED_LATCHED
SENSOR_FAULT
COMM_FAULT
INTERNAL_FAULT
MAINTENANCE
```

### قواعد الكود

- لا يستخدم أي Sample إذا `valid=false`.
- كل Channel له timestamp/age، ولا تعتبر عينة قديمة صالحة.
- Timeout لكل Bus وSPI؛ لا توجد حلقات انتظار بلا حد.
- Independent watchdog وBrownout reset.
- Fixed-width integer types، ويفضل fixed-point للحرارة.
- لا Dynamic allocation في مسار التشغيل.
- إعدادات Versioned وبـCRC، وDefaults آمنة عند فساد الذاكرة.
- تسجيل First-out cause: أول سبب فصل لا يضيع بسبب أعطال لاحقة.
- Debounce للأزرار، وRate limit للكتابة إلى EEPROM/Flash.
- Compile warnings as errors، Static analysis، Unit tests، Integration/HIL tests.
- فصل Driver كل نوع Sensor عن منطق الحماية.
- Update mechanism لا يسمح بصورة Firmware غير صحيحة؛ Bootloader قرار لاحق.

## 12. خريطة Modbus مبدئية

لا نعتمد الأرقام نهائيًا الآن، لكن نقسمها هكذا:

| المجموعة | Read/Write | المحتوى |
|---|---|---|
| Identification | Read only | Model, HW rev, FW version, serial number |
| Live readings | Read only | Temperature x10, valid, fault bits, age لكل قناة |
| Protection state | Read only | Safe/Trip, first-out channel/cause, latch, relay feedback |
| Commands | Controlled write | Remote OFF/ON request, ACK request |
| Configuration | Protected write | Setpoint, reset threshold, channel enable, address/baud |
| Diagnostics | Read/clear controlled | Reset counters, comm errors, sensor faults, uptime |

حماية من الخطأ/العبث:

- Remote ON طلب وليس إجبارًا، ويمر عبر Local safety gate.
- Function codes والـregisters المسموح بكتابتها محدودة.
- إعدادات العناوين لا تتغير عرضيًا، وكل جهاز له عنوان فريد.
- Configuration write يحتاج unlock sequence/physical enable حسب تقييم المخاطر.
- الـCRC الخاص بـModbus يكشف خطأ النقل، لكنه ليس Authentication أو Cybersecurity.

## 13. المعايير التي يجب تقييمها — لا ندعي المطابقة بعد

| المرجع | لماذا قد ينطبق؟ | المطلوب الآن |
|---|---|---|
| IEC 61326-1:2020 | EMC لمعدات القياس والتحكم | تعريف البيئة وخطة immunity/emissions |
| IEC 61010-1 + AMD1 | سلامة معدات القياس والتحكم | تقييم المخاطر والعزل والحرارة والحريق |
| IEC 60204-1:2016+A1:2021 | المعدات الكهربائية للماكينات | تنسيق الوحدة مع لوحة الماكينة ودوائر التحكم |
| IEC 61511 | Safety instrumented systems في Process industry | ينطبق فقط إذا هذه وظيفة SIF/SIS؛ يحتاج Safety lifecycle وSIL study |
| IEC 60079 series | الأجواء القابلة للانفجار | ينطبق إذا الحساس/الكابل/الوحدة داخل أو مرتبط بـHazardous Area |
| ISA/IEC 62443 | Cybersecurity لأنظمة التحكم | عند وجود شبكة/Gateway أو متطلبات أمن OT |
| IPC-2221 / IPC-2152 / IPC-4761 | Layout عام، تيار، Vias | قواعد PCB وDFM موثقة |
| IEC 60664 principles | Creepage/clearance والعزل | حساب الحدود من ظروف الاستخدام الحقيقية |

إذا كان Trip يحمي أشخاصًا أو يمنع حريقًا/انفجارًا أو حادث Process، فلا يكفي
أن نقول إن الكود Fail-safe. الشركة/مهندس السلامة يحدد هل الوظيفة SIF، والـSIL،
والاستقلالية المطلوبة. إلى أن يحدث ذلك، هذه الوحدة Prototype monitoring/control
ولا تحل محل جهاز حماية معتمد قائم.

## 14. خطة التحقق والاختبار

### 14.1 مرحلة المتطلبات والمعاينة

- تسجيل موديلات الحساسات والجهاز القديم والـVFD/Contactor/PLC.
- قياس/تأكيد continuity بين طرف الحساس والغلاف لإثبات Grounded junction.
- توثيق نوع الكابل، المقاس، shielding، مساره، والـjunctions/connectors.
- تحديد Hazardous Area classification وحدودها.
- تحديد كل Safe state وحالات إعادة التشغيل والـACK.

### 14.2 Proof-of-concept للقياس قبل PCB الثماني قنوات

- قناة واحدة بالكابل الحقيقي 50 m والحساس الحقيقي.
- مقارنة بالـArchitecture المرشحة: isolated TC input مقابل 4–20 mA transmitter.
- تشغيل VFD/Contactor قريبًا وقياس drift/faults.
- اختبار فرق جهد أرضي مسيطر عليه ضمن حدود معدات المعمل.
- اختبار open circuit وshort/reversed polarity.
- مقارنة مع calibrator أو جهاز مرجعي traceable عبر عدة نقاط حرارة.

**بوابة قرار:** لا نرسم Final 8-channel PCB قبل نجاح هذه المرحلة واختيار
Architecture القياس.

### 14.3 Prototype هندسي

- Prototype قناتين أولًا: قناتان تثبتان channel-to-channel behavior والعزل.
- اختبار 24 V input، brownout، reverse polarity، load transients.
- اختبار RUN_PERMIT كـenergized-to-run وفقد التغذية.
- اختبار RS-485 بأقصى عدد وحدات وطول/Topology حقيقيين.
- Fault injection لكل قناة، وانقطاع الاتصال، وتعطل الذاكرة والإعدادات.

### 14.4 نسخة 8 قنوات

- ERC/DRC وSchematic-to-PCB cross-check.
- مراجعة Datasheet/MPN/footprint لكل جزء، وليس اسمًا عامًا فقط.
- مراجعة Isolation barriers وcreepage/clearance مستقلة.
- Power/thermal budget وWorst-case analysis.
- EMC pre-compliance: ESD, EFT/burst, surge, conducted/radiated immunity/emissions
  وفق Applicability الفعلية.
- Environmental soak، power cycling، 8-channel accuracy، long-duration test.
- Manufacturing test fixture وCoverage لكل قناة وكل خرج واتصال.

### 14.5 تجربة ميدانية تدريجية

1. تشغيل Read-only بالتوازي مع الجهاز الحالي؛ لا تتحكم الوحدة الجديدة في الموتور.
2. مقارنة القراءات والـfault logs لوقت كافٍ وتحت تشغيل VFD الحقيقي.
3. تشغيل Alarm فقط.
4. تشغيل Interlock بعد موافقة كهرباء/Process/Safety وخطة رجوع واضحة.
5. لا يزال جهاز الحماية المعتمد موجودًا حتى إغلاق التحقق الرسمي.

## 15. ما يثبته Proteus وما لا يثبته

Proteus مفيد لاختبار:

- Pin mapping وLCD والأزرار.
- منطق Setpoint/Hysteresis/Latch.
- Modbus frames مبدئيًا.
- تغير القراءة وحالات Software fault المحقونة.

لا يثبت:

- دقة MAX31856 الحقيقية وCold-junction gradients.
- Grounded thermocouple على 50 m.
- Isolation أو creepage/clearance.
- EMI من VFD/Contactor أو ESD/EFT/Surge.
- Contact rating أو العمر الميكانيكي للريلاي.
- Safety integrity أو صلاحية Hazardous Area.

## 16. مراحل التنفيذ والتسليم

### Phase 0 — تثبيت المتطلبات

الناتج: إجابات الأسئلة في القسم 17، صور وموديلات الأجهزة، I/O list، Cause & Effect.

### Phase 1 — اختيار واجهة القياس

الناتج: تقرير تجربة 50 m grounded sensor، واختيار A أو B أو C بالأسباب والتكلفة.

### Phase 2 — Schematic prototype

الناتج: Power tree، قناتان قياس، MCU، RS-485، مخارج، UI، وحسابات حماية وعزل.

### Phase 3 — Firmware base

الناتج: State machine، 8-channel scheduler، configuration، Modbus map، unit tests.

### Phase 4 — 8-channel PCB

الناتج: KiCad source، BOM بقطع محددة MPN، ERC/DRC، fabrication outputs، test plan.

### Phase 5 — Verification

الناتج: تقارير functional/accuracy/fault/EMC/thermal/communication واختبار تصنيع.

### Phase 6 — Field pilot

الناتج: مقارنة مع الجهاز الحالي، سجل الأعطال، Sign-off، وخطة صيانة/رجوع.

## 17. الأسئلة التي يجب أخذ إجاباتها من المهندس/الموقع

1. ما موديل الحساس الكامل وداتا شيته؟ وهل كل الثمانية Grounded فعلًا؟
2. ما نوع وسُمك الكابل لمسافة 50 m؟ هل هو K-type extension-grade؟ وهل Shielded؟
3. أين يوصل Shield الآن: عند الحساس، أم البانل، أم الطرفين، أم غير موصل؟
4. ما موديل جهاز الحماية الحالي، وصورة الـterminal diagram والـmanual؟
5. هل الجهاز الحالي Isolated channel-to-channel أو يستخدم Transmitters خارجية؟
6. هل الحساسات أو الكابلات تمر داخل Hazardous Area؟ ما Zone/Gas group/Temperature class؟
7. ما وظيفة Trip بالضبط: إنذار فقط أم حماية من حريق/انفجار/تلف خطير؟
8. هل Trip أي قناة يفصل موتورًا واحدًا أم لكل قناة Load مختلف؟
9. هل لكل قناة Setpoint مستقل؟ وما Trip/Reset values والـallowed ranges؟
10. هل Trip يظل Latched حتى ACK؟ من أين يقبل ACK: زر، Master، أم الاثنين؟
11. عند Sensor fault: هل المطلوب Trip فوري دائمًا؟
12. عند فقد الاتصال بالـMaster: هل الوحدة تفصل أم تستمر محليًا؟
13. ما موديل VFD/Contactor/PLC؟ وما جهد/تيار مدخل RUN/ENABLE؟
14. هل المطلوب RUN/STOP فقط أم أيضًا Speed reference؟ وإن كان مطلوبًا فما واجهته؟
15. كم لوحة Slave كحد أقصى، وما المسافة الكلية للـRS-485 والـTopology؟
16. ما مدى 24 V الفعلي، ومصدره، والأحمال الموصلة عليه؟
17. حرارة البانل، الرطوبة، الاهتزاز، IP rating، ونوع التركيب DIN rail أو Door/Panel؟
18. هل توجد متطلبات شركة داخلية أو اعتماد/Inspection محدد قبل التشغيل؟

## 18. سجل القرارات الحالي

| القرار | الحالة | السبب |
|---|---|---|
| 8 قنوات | Accepted baseline | طلب المشروع |
| OFF أعلى أولوية من ON | Accepted | الحماية لا تُتجاوز بأمر Remote |
| Local trip مستقل عن الشبكة | Accepted | منع single dependency على Master |
| Dry-contact RUN_PERMIT | Recommended | تكامل كلاسيكي واسع مع عزل وظيفي |
| AUX_ALARM منفصل | Recommended | فصل الحماية عن التشخيص |
| RS-485 + Modbus RTU | Recommended | Multi-drop وPLC/VFD integration |
| 4–20 mA/0–10 V output | Optional pending load manual | ليس مطلوبًا لـRUN/STOP |
| PWM | Deferred / not generic | يعتمد على Manual جهاز محدد |
| 8 MAX31856 على Ground واحد | Rejected for field | grounded tips + 50 m + ground loops |
| 4–20 mA head transmitters | Preferred candidate | robust long-distance industrial signal |
| isolated TC channel per input | Second candidate | يحتفظ بالحساس الخام مع تكلفة/تعقيد أكبر |
| MCU | Open: ATmega32A or STM32G0 | بعد حصر I/O والـArchitecture |
| ESP32 | Gateway/Master candidate | IoT منفصل عن local trip path |
| Final PCB الآن | Blocked by measurement architecture | يلزم proof-of-concept أولًا |

## 19. شروط No-Go

- لا نوصل 24 V باللوحة الحالية ذات مدخل 5 V.
- لا نكرر MAX31856 ثماني مرات على أرضي واحد مع الحساسات الـgrounded دون عزل مثبت.
- لا نسمي Relay contact «أي فولت» دون ratings وتصميم عزل موثق.
- لا نستخدم PWM مع VFD لمجرد أنه متاح من المتحكم.
- لا نسمح لأمر Master ON بتجاوز Local trip أو sensor fault.
- لا نعتبر DRC=0 أو Proteus successful دليل Field readiness.
- لا نزيل جهاز الحماية الحالي قبل Pilot ومراجعة المخاطر والـsign-off.
- لا ندعي IEC/SIL/Ex compliance من دون تطبيق المعيار والاختبارات/الاعتماد المطلوب.

## 20. الخطوة التالية العملية

قبل أي تعديل جديد للـPCB أو Firmware:

1. اجمع إجابات القسم 17، وأهمها موديل الحساس والجهاز القديم والـVFD والـZone.
2. اختبر أو أكد أن الطرف Grounded فعلًا.
3. اختر بالتجربة بين 4–20 mA transmitter وisolated thermocouple input.
4. اعمل I/O list وCause & Effect مع المهندس.
5. بعد توقيع Baseline، نبدأ Schematic جديدًا لنسخة 8 قنوات بدل ترقيع لوحة القناة الواحدة.

## 21. المصادر الفنية الأولية

- Analog Devices, MAX31856 datasheet:  
  https://www.analog.com/media/en/technical-documentation/data-sheets/max31856.pdf
- Analog Devices, MAX31856 FAQ — grounded tip is not advised:  
  https://ez.analog.com/data_converters/a/documents/c/max31856-faq
- Analog Devices, MAX31856 grounded thermocouple isolation guidance:  
  https://ez.analog.com/cn/interface-isolation/a/wiki/c/max31856mud-faq
- Analog Devices, The Basics of Thermocouples — grounded junction and long leads:  
  https://www.analog.com/en/resources/design-notes/the-basics-of-thermocouples.html
- Analog Devices, Thermocouple measurement design essentials — long-cable noise:  
  https://www.analog.com/en/resources/technical-articles/thermocouple-temperature-measurement-system-design-essentials.html
- Modbus Organization, specifications and Serial Line Guide V1.02:  
  https://www.modbus.org/modbus-specifications
- ABB ACS580 hardware manual — example of DI, analog references and Modbus RTU:  
  https://library.e.abb.com/public/2412cccc15634c51932d3a8a590b727e/EN_ACS580-01_HW_D_A5_screen.pdf
- IEC 61326-1:2020:  
  https://webstore.iec.ch/en/publication/62793
- IEC 61010-1:2010+A1:2016:  
  https://webstore.iec.ch/en/publication/4279
- IEC 60204-1:2016+A1:2021:  
  https://webstore.iec.ch/en/publication/71256
- IEC 61511-1:2016+A1:2017:  
  https://webstore.iec.ch/en/publication/61289
- IEC 60079-0:2026:  
  https://webstore.iec.ch/en/publication/71519
- ISA/IEC 62443 series overview:  
  https://www.isa.org/standards-and-publications/isa-standards/isa-iec-62443-series-of-standards

