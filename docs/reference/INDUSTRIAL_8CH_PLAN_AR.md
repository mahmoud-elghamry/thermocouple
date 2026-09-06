> **مرجع فقط — لم يعد مصدر الحقيقة.**
> الحالة الحالية في `docs/STATE.md`، والمشاكل المفتوحة في `docs/ISSUES.md`،
> والقرارات في `docs/decisions/`. عند أي تعارض، تلك الملفات هي الصحيحة.
> نقطة البداية لأي agent هي `AGENTS.md` في جذر المستودع.

# خطة تطوير وحدة حماية حرارة صناعية — 8 قنوات Thermocouple

**حالة الوثيقة:** Single Source of Truth للمتطلبات والقرارات وحالة التنفيذ
**آخر تحديث:** 2026-09-06
**المشروع الحالي:** Firmware وProteus prototype لثماني قنوات، مع PCB قناة واحدة فقط؛ وليس منتجًا صناعيًا معتمدًا بعد

## 0. ملخص الحالة الحالية وتسليم السياق لأي Agent

هذا القسم هو أول ما يقرأه Codex أو Claude أو أي مهندس جديد. بعد أي تغيير مادي في
المتطلبات أو الكود أو المحاكاة أو الـPCB يجب تحديث **هذا الملف وتاريخ آخر تحديث**،
مع الفصل بين: تم تنفيذه، تم اختباره، وما زال قرارًا مقترحًا.

### 0.1 ما تم تنفيذه واختباره

- يوجد Firmware منفصل للـMAX31856 قناة واحدة، ولـMAX6675 قناة واحدة، ولـMAX6675
  ثماني قنوات.
- أُعيد بناء الصور الثلاث محليًا بتاريخ 2026-09-04 باستخدام `firmware/build.ps1`
  مع `-Wall -Wextra -Werror`، ونجح الـbuild والـlink وتوليد ملفات HEX.
- نجحت Host unit tests لمنطق عرض الحرارة والـhysteresis ولـ8-channel trip latch،
  sensor fault، وشروط ACK.
- صورة المحاكاة الحالية لثماني قنوات هي:
  `firmware/build/thermocouple_meter_max6675_8ch.hex`.
- نقطة الفصل الافتراضية لنسخة الثماني قنوات هي 200.0 C ومجمعة في
  `firmware/include/app/app_config.h`، وليست ثابتًا مخفيًا داخل منطق التطبيق.
- المستخدم شغّل مشروع Proteus وأكد أن المحاكاة تعمل. ملف المشروع المتتبع هو
  `semulation/thermocouble [Autosaved]f.pdsprj`.

### 0.2 ما لم يكتمل إثباته بعد

- لم تُسجل بعد Regression كاملة داخل Proteus لكل الحالات: الثماني قراءات، كل
  الأزرار، تجاوز كل قناة للـsetpoint، open sensor، بقاء الـlatch، شروط ACK،
  وقطبية خرج `RUN_PERMIT`.
- ظهر سابقًا تحذير Proteus باسم `Logic contention(s) detected on net #00006` على
  خط SO/MISO المشترك. المحاكاة اشتغلت، لكن لا يُعتبر التحذير مغلقًا حتى يُعاد
  الاختبار بعد التأكد أن لكل MAX6675 خط CS مستقل وأن الموديلات غير المختارة تجعل
  SO في High-Z.
- الـPCB في `pcb/thermocouple_meter.kicad_pcb` لوحة **قناة واحدة** مع MAX31856
  ولا تُعدَّل. يوجد الآن **Engineering Prototype لثماني قنوات** في `pcb/8ch/`
  بأربع طبقات وثلاث جزر عزل — تفاصيله وأرقام فحوصه في القسم 22. هو نموذج هندسي
  وليس لوحة إنتاج: العزل فيه **بين المجموعة والمتحكم** ولا يعزل القنوات عن
  بعضها، ولم تُجرَ عليه أي اختبارات ضوضاء أو EMC أو حساسات حقيقية.
- Proteus يثبت منطق البرنامج والتوصيل الرقمي فقط؛ لا يثبت سلوك كابل 50 m أو
  grounded junction أو EMC أو دقة القياس الميدانية.

### 0.3 ترتيب القراءة والعمل للـAgent

1. اقرأ هذه الوثيقة كاملة قبل اقتراح Architecture أو تعديل PCB.
2. استخدم `docs/CONNECTIONS.md` كمرجع البنات الفعلي للمحاكاة الحالية.
3. استخدم `docs/SOFTWARE_ARCHITECTURE_AR.md` لفهم طبقات MCAL/HAL/APP.
4. لا تعدّل PCB القناة الواحدة على أنها PCB الثماني قنوات. مشروع الثماني قنوات
   منفصل في `pcb/8ch/` وله README خاص به؛ اقرأ القسم 22 قبل لمسه.
5. لا تصف أي نتيجة بأنها Production-ready بناءً على build أو Proteus أو DRC فقط.

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

**تصحيح مهم:** MAX31856 أحدث وأفضل من MAX6675 في الدقة، أنواع الحساسات، كشف
الأعطال، فلترة 50/60 Hz وحماية الدخل، لكنه **ليس Galvanic Isolator** ولا يفصل
T+/T- كهربائيًا عن AGND/DGND. لذلك حداثته لا تحل تلقائيًا grounded tip أو 50 m.

العزل المشترك لمجموعة الثماني قنوات يعزل المجموعة عن المتحكم/الماستر، لكنه لا
يعزل القنوات عن بعضها. يمكن دراسته كحل وسط فقط إذا أثبت القياس أن أغلفة الحساسات
الثمانية على نفس الجزء المعدني ونفس الـequipotential bonding ولا يوجد فرق جهد
مؤثر بينها. هذه فرضية اختبار وليست قرارًا منفذًا في اللوحة الحالية.

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
| MAX31856 وحده يحل grounded tip | Rejected | واجهة قياس محسنة لكنها غير معزولة كهربائيًا |
| عزل مشترك للثماني قنوات | Conditional PoC only | يعزل المجموعة عن النظام ولا يعزل القنوات عن بعضها |
| 4–20 mA head transmitters | Preferred candidate | robust long-distance industrial signal |
| isolated TC channel per input | Second candidate | يحتفظ بالحساس الخام مع تكلفة/تعقيد أكبر |
| MCU | Open: ATmega32A or STM32G0 | بعد حصر I/O والـArchitecture |
| ESP32 | Gateway/Master candidate | IoT منفصل عن local trip path |
| 8-channel engineering-prototype PCB | Implemented, not released | 4 طبقات، ثلاث جزر عزل، routing بـFreerouting؛ انظر القسم 22 لأرقام DRC/ERC والقيود |
| Field-release PCB | Blocked by measurement validation | يلزم proof-of-concept للكابل والحساسات ثم اختبارات واعتماد |

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

الترتيب العملي الحالي:

1. أكمل Regression المحاكاة للحالات المذكورة في 0.2 وسجل النتيجة في هذه الوثيقة.
2. اجمع إجابات القسم 17، وأهمها موديل الحساس والجهاز القديم والكابل والشيلد والـZone.
3. قس continuity وفرق الجهد بين أغلفة الحساسات/أرضي الماكينة وأرضي البانل بدل
   افتراض أن كل النقاط متساوية.
4. اختبر قناة ثم قناتين بالكابل الحقيقي 50 m، بما في ذلك تشغيل الموتور/VFD،
   وقارن: common isolated island، per-channel isolation، و4–20 mA transmitter.
5. اعمل I/O list وCause & Effect مع المهندس وثبّت سياسة Trip/ACK/Remote.
6. بعد اختيار Architecture القياس، ابدأ Schematic وPCB جديدين لنسخة 8 قنوات
   بدل ترقيع لوحة القناة الواحدة.

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

## 22. حالة تنفيذ لوحة الثماني قنوات — 2026-09-06

هذه الحالة تخص **Engineering Prototype** فقط ولا تلغي شروط No-Go ولا اختبارات
الكابل الحقيقي المذكورة أعلاه. الأرقام هنا مقروءة من تقارير الفحص في
`pcb/8ch/`، وليست تقديرًا.

### 22.1 المعمارية المنفَّذة

المشروع في `pcb/8ch/` منفصل تمامًا عن لوحة القناة الواحدة في `pcb/`.

- **اللوحة:** 250 × 140 mm، أربع طبقات.
- **الطبقات:** F.Cu إشارات + صبّة أرضي، In1.Cu أرضيات
  (`GND_SENS` / `GND_CTRL` / `GND_RS485`)، In2.Cu تغذيات
  (`+3V3_SENS` / `+5V_CTRL` / `+5V_RS485`)، B.Cu إشارات + صبّة أرضي + حلقة
  Chassis/PE. **لا تمر أي إشارة داخل In1 أو In2**، فيبقى لكل مسار خارجي مسار
  رجوع متصل تحته مباشرة، ويعمل زوج In1/In2 كمكثف بيني موزّع.
- **ثلاث جزر نحاسية** يفصلها شريط بلا نحاس: جزيرة الحساسات (x 6→145)، جزيرة
  التحكم (x 151.5→244)، جزيرة RS-485 (x 214→244، y 103→134). العبور الوحيد
  للإشارات عبر U10/U11 (ISO7760/ISO7761) وU15 (ADM2587E). الأشرطة مكتوبة في
  اللوحة كـ**Rule Areas** حتى لا يستطيع الـautorouter عبورها، ولتكون النية
  مرئية لأي مراجع.
- **شبكة رابعة `CHASSIS_SHIELD`** كحلقة على B.Cu على بعد 3 mm من الحافة،
  مربوطة بأربع فتحات تثبيت M3 مطلية وبـJ1.3 وJ4.4 وأغلفة الحساسات الثمانية،
  ومعزولة عن الأرضيات الثلاثة عمدًا حتى لا يتحول تيار الشيلد إلى ground loop.

### 22.2 قواعد التصميم انتقلت إلى مشروع KiCad

كانت عروض المسارات والـvias والـclearance مكتوبة داخل سكربت بايثون، فلا يراها
من يفتح المشروع في KiCad ولا يفحصها الـDRC. أصبحت الآن:

- **ثمانية Netclasses** في `thermocouple_8ch.kicad_pro`: `Default`،
  `SensorSignal`، `SensorPower`، `CtrlPower`، `Power24V`، `RelayContact`،
  `RS485`، `Chassis`.
- **قواعد مخصّصة** في `thermocouple_8ch.kicad_dru`: عزل 3 mm بين كل جزيرتين،
  1.5 mm للـrelay dry contact، 1.5 mm للـchassis، وحد أدنى لـannular ring
  لمسارات الحساسات.
- **تفعيل فحوصات الـcourtyard** (`missing_courtyard`، `courtyards_overlap`،
  `malformed_courtyard`) — كانت `ignore`، وهو بالضبط البند P-02 في
  `docs/DESIGN_REVIEW_AR.md`.

رقم الـ3 mm مصدره أضيق عبور فعلي على اللوحة: مسافة أرجل موديول IA0505S نفسه
(خطوة 5.08 mm تترك فجوة نحاس 3.23 mm). باقي العبورات (ISO7760/ISO7761/ADM2587E
في عبوات SOIC-W) تترك 7.25 mm. **هذا عزل وظيفي وليس اعتمادًا لحاجز أمان**، ولم
تُجرَ عليه دراسة creepage/clearance وفق IEC 61010 بجهد تشغيل ودرجة تلوث محددين.

### 22.3 الـRouting: من سكربت داخلي إلى Freerouting

كان `generate_board.py` يحتوي autorouter مكتوبًا يدويًا (A* على grid 0.5 mm،
حركة أفقية/رأسية فقط، بلا rip-up & retry، ونموذج clearance تقريبي). نتيجته كانت
**381 مخالفة DRC** و**5 شبكات غير موجّهة** و~4000 قطعة مسار غير قابلة للتعديل
اليدوي (البند H-13 في المراجعة).

المسار الحالي:

```
pcbnew  →  .dsn  →  Freerouting 2.4.1  →  .ses  →  pcbnew
```

مع تعديلين على ملف الـDSN قبل التمرير:

1. KiCad يكتب كل طبقات النحاس `(type signal)`. تُعاد In1/In2 كـ`(type power)`
   حتى يبقى الـrouting على F.Cu وB.Cu فقط ولا تتقطّع الـplanes.
2. حلقة الـChassis/PE الموجودة مسبقًا تُعلَّم `(type protect)` حتى لا يفكّها
   الـoptimizer.

**ملاحظة تشغيلية:** Freerouting نفسه يحذّر أن الـoptimization متعدد الخيوط
مكسور ويولّد clearance violations؛ لذلك الافتراضي في `route.py` أصبح
`--threads 1`.

الأدوات الخارجية (Freerouting 2.4.x وJava 25) ليست داخل المستودع. Freerouting
2.4.1 مبني على class-file version 69 فلا يعمل على Java 21.

### 22.4 أخطاء حقيقية وُجدت وأُصلحت

| # | الخطأ | الأثر لو خرج للتصنيع |
|---|---|---|
| 1 | **Q1 (2N7000): الرجل 1 (Source) على `RELAY_GATE` والرجل 2 (Gate) على `GND_CTRL`** | الـGate مربوط على الأرضي وVgs سالب دائمًا → الترانزستور لا يفتح أبدًا → الريلاي لا يعمل → `RUN_PERMIT` لا يتفعّل → **الماكينة لا تشتغل إطلاقًا** |
| 2 | U15 (ADM2587E) موضوع بحيث تقع أرجل `GND_CTRL` فوق منطقة `GND_RS485` | خرق فعلي لحاجز العزل |
| 3 | JP1/R34/JP2 (طرفية وbias الـRS-485) داخل جزيرة التحكم بدل الجزيرة المعزولة | نفس الشيء |
| 4 | J3 وJ4 خارج حدود اللوحة (J4 حتى 140.15 mm واللوحة 140 mm) | فشل تصنيع |
| 5 | J4 مقلوب — فتحة السلك تواجه داخل اللوحة | لا يمكن توصيله في البانل |
| 6 | J2 (هيدر LCD) وU12 (IA0505S) بزوايا تدوير خاطئة | J2 يمتد رأسيًا 41 mm فوق مكونات أخرى؛ جسم U12 خارج أرجله |
| 7 | D5/D6 courtyards متداخلة | تصادم ميكانيكي عند التجميع |
| 8 | الإشارات موجَّهة داخل طبقتي الـplanes | مصدر معظم الـ304 clearance ويقطّع مسار الرجوع |
| 9 | `DIP-40_Socket_LongPads`: فجوة 0.14 mm بين الأرجل | لا يمكن تمرير أي مسار بين أرجل المتحكم؛ استُبدل بـ`DIP-40_Socket` (فجوة 0.94 mm) |

### 22.5 بنود `DESIGN_REVIEW_AR.md` — ما ينطبق وما لا ينطبق

المراجعة كُتبت على لوحة القناة الواحدة عند `c8ae6f5`. التصنيف بعد الفحص الفعلي:

**كانت معالَجة أصلًا في تصميم 8ch — لم يُعَد تنفيذها:**
H-02 (2N7000 بدل ترانزستور ثنائي القطبية)، H-09 (PTC + SS34 + TVS)،
H-10 (اللوحة كلها 5 V فلا يلزم level shifting)، H-11 (C52 على RESET)،
H-08 (تسع نقاط اختبار)، P-01 (Schematic موجود).

**نُفِّذت في هذه الجولة:**
- **H-01** — أربع طبقات مع planes مخصّصة وصبّات أرضي على الطبقات الخارجية.
- **H-03** — R_p/R_n وC_cm_p/C_cm_n متماثلة تمامًا حول محور T+/T−، وفاحص
  `check_board.py` يتحقق من ذلك في كل توليد.
- **H-04** — كل مكثف decoupling على بعد ≤ 4 mm من رجل تغذيته (3.80 mm لـAVDD،
  2.58 mm لـDVDD)، وكل رجل تغذية SMD لها via إلى الـplane.
- **H-06** — MAX31856 مُدار 270° فتقع أرجل T+/T− مواجهة للطرفية بالترتيب الصحيح
  بلا تقاطع، والمسافة بين الطرفية والشريحة نزلت من 23 mm إلى **15.8 mm**، مع
  صبّة نحاس مشتركة تجعلهما أقرب إلى التساوي الحراري.
- **H-07** — كل الـ167 reference designator ظاهرة، ومعادة التوزيع آليًا بعيدًا
  عن أجسام المكونات والأرجل.
- **H-13** — Freerouting بزوايا 45° بدل الـA* الأورثوجونالي.
- **P-02** — فحوصات الـcourtyard مفعّلة.
- **P-03 (جزئيًا)** — هوية اللوحة مطبوعة على الـsilkscreen:
  `THERMO-8CH REV A0 2026-09`.

**قرار موثّق بدل تنفيذ — H-05 (DRDY/FAULT):**
أرجل `DRDY` و`FAULT` الستة عشر غير موصولة بالمتحكم. السبب هندسي وليس سهوًا:
ISO7760 مستهلك بالكامل (6 قنوات أمامية) وISO7761 مستهلك (5 أمامية + قناة عكسية
لـMISO)، فتمرير 16 إشارة إضافية عبر الحاجز يتطلب عازلًا ثالثًا ومنطق OR للأعطال.
الـfirmware يقرأ سجل الأعطال (0x0F) في كل عيّنة. وُضعت لها **No-Connect markers**
في السكيماتك بدل تركها كـlabels معلّقة.

**لا ينطبق على 8ch:** P-04، P-05، F-01…F-13 (بنود Firmware وعملية بناء).

**ما زال مفتوحًا:** P-06 (المكونات السلبية بلا MPN)، P-07 (اسم ملف المحاكاة).

### 22.7 نتائج الفحص — 2026-09-06

الأرقام مقروءة من `pcb/8ch/erc-report.rpt` و`pcb/8ch/drc-report.rpt`.

| الفحص | قبل | بعد |
|---|---|---|
| **ERC — أخطاء** | 7 | **0** |
| ERC — تحذيرات | 189 | 171 (كلها `endpoint_off_grid`) |
| **DRC — إجمالي المخالفات** | 381 | **6** |
| clearance | 304 | **0** |
| shorting_items | 19 | **0** |
| tracks_crossing | 22 | **0** |
| via_dangling | 7 | **0** |
| hole_clearance | 6 | **0** |
| zones_intersect | 2 | **0** |
| starved_thermal | 2 | **0** |
| solder_mask_bridge | 2 | **0** |
| footprint_symbol_field_mismatch | 146 | **0** |
| silk_overlap | 10 | 5 (تحذير) |
| silk_over_copper | 3 | 1 (تحذير) |
| **unconnected_items** | 46 | **10** |
| Schematic ↔ PCB parity | — | **0** |

المخالفات الست المتبقية كلها تحذيرات silkscreen، وليست أخطاء تصنيع.

### 22.8 لماذا اللوحة ليست جاهزة لإخراج Gerbers

**السبب الوحيد المتبقي: عشر توصيلات لم يكملها الـautorouter.**

| الرجل | الشبكة | الملاحظة |
|---|---|---|
| C42.1 | `+3V3_SENS` | مكثف تفريع عند U10 جانب الحساسات |
| C44.1 | `+3V3_SENS` | مكثف تفريع عند U11 جانب الحساسات |
| C48.1 | `+3V3_SENS` | مكثف خرج الـLDO |
| U4.5 | `+3V3_SENS` | AVDD للقناة 3 |
| U5.5 | `+3V3_SENS` | AVDD للقناة 4 |
| U15.6 | `RS485_DE` | خرج المتحكم إلى ADM2587E |

الخمسة الأولى تحتاج via واحدة لكل رجل تنزل إلى plane الـ`+3V3_SENS`، لكن المساحة
حولها مزدحمة فرفض فاحص التصادم كل المواضع. السادسة مسار إشارة قصير غير مكتمل.

هذا **عمل routing يدوي لعشر توصيلات في KiCad** — نصف ساعة لمهندس. لم يُنفَّذ آليًا
لأن دفع vias بالقوة في مساحة مزدحمة هو بالضبط ما ولّد 88 short و16 مخالفة
hole-clearance في محاولة سابقة، والفشل المعلن أفضل من لوحة تبدو نظيفة وهي ليست كذلك.

**لم تُولَّد أي ملفات Gerber.** الشرط المعلن في القسم 20 وفي README هو DRC نظيف
من أخطاء التصنيع الحقيقية، و10 توصيلات ناقصة ليست حالة نظيفة.

### 22.9 الفحوصات الهيكلية

`pcb/8ch/check_board.py` يفحص ما لا يفحصه DRC، ويُشغَّل مع كل توليد:

| الفحص | النتيجة |
|---|---|
| كل رجل في جزيرة العزل الصحيحة | ✅ |
| لا نحاس داخل أشرطة العزل | ✅ (عدا رجل U12.4 المتوقعة، انظر 22.6) |
| قرب مكثفات التفريع من أرجلها | ✅ (3.80 mm لـAVDD، 2.58 mm لـDVDD) |
| مسافة الوصلة الباردة | ✅ 15.8 mm لكل القنوات الثماني |
| تماثل فلتر الدخل | ✅ لكل القنوات الثماني |
| اكتمال التوجيه | ❌ 10 توصيلات ناقصة |

بالإضافة إلى: صفر تداخل courtyard، صفر مكوّن خارج حدود اللوحة، وكل الـ167
footprint لها courtyard معرّف.

الفحص البصري في 3D Viewer (`pcb/8ch/output/board_3d_top.png` و`board_3d_bottom.png`)
يؤكد: الجزر الثلاث منفصلة، شريط العزل خالٍ من النحاس، فتحات الطرفيات كلها ناحية
حواف اللوحة، وحلقة الـPE محيطية على B.Cu.

### 22.6 قرارات تحتاج مراجعة بشرية

1. **IA0505S غير منظّم (Unregulated).** الموديول ثنائي الخرج ±5 V، وحمل جزيرة
   الحساسات ~12% من طاقته. خرج الموديولات غير المنظّمة عند حمل خفيف يرتفع فوق
   القيمة الاسمية، والحد الأقصى الموصى به لدخل AP2112K هو 6 V. **يجب قياس الخرج
   الفعلي على الهاردوير أو الانتقال إلى موديول معزول منظّم.** ولم يُغيَّر في
   الـBOM لأن ذلك قرار شراء وتغيير footprint.
2. **الرجل 4 في U12 (‎−Vout غير المستخدم) تقع داخل شريط العزل.** هذا حتمي:
   خطوة أرجل الموديول 2.54 mm والشريط 6.5 mm. كهربائيًا الرجل تابعة للجانب
   الثانوي (الحساسات)، فالحاجز الفعلي هو الرجل 2 إلى الرجل 4 = فجوة 3.23 mm.
3. **مسافة حلقة الـPE محكومة بهندسة الموصلات.** خطوة الطرفيات 5.00 mm تجعل
   المسافة بين رجل الشيلد ورجل الإشارة المجاورة 2.4 mm نحاسيًا، ولذلك قاعدة
   الـchassis 1.5 mm. ليست فصلًا مقنّنًا للجهد العالي.
4. **السكيماتك صحيح كهربائيًا لكنه ليس رسمًا قابلًا للمراجعة.** الملف مولَّد
   كرموز + labels على الأرجل، **بصفر أسلاك وصفر junctions**، على ورقة A4 واحدة
   بها 171 رمزًا. يخرج netlist صحيحًا وينجح في ERC، لكن لا يستطيع مهندس تتبّع
   إشارة فيه أو التوقيع عليه. إعادة رسمه كأوراق هرمية موصّلة بأسلاك حقيقية عمل
   متبقٍ. تحذيرات `endpoint_off_grid` الـ171 كلها من هذا السبب.
5. **جزيرة الحساسات المشتركة** تبقى قرار Prototype مشروط كما في القسم 3، ولا
   تعزل القنوات عن بعضها.
