# مراجعة Thermo — المعمارية والتنفيذ والتكلفة

2026-10-09 — مراجعة الشجرة عند commit `5f8abc6`، قبل أي تعديل تصميم من هذه المراجعة.

**الحكم: أصل المعمارية قابل للتنفيذ، لكن النسخة الحالية تحتاج إصلاح Layout قبل طلبها. لا توجد بعد نسخة Firmware تشغّل وتحمي 24 قناة.** إكمال التوصيلات خطوة صحيحة، وليس دليل جاهزية المنتج. لا أوصي بإعادة اختراع الجهاز أو تغيير المعالج الآن؛ أوصي بإصلاح المناطق الحساسة، وإغلاق واجهات البرنامج والميكانيكا والتصنيع، ثم نموذج تجريبي مؤهل للاختبار.

لم أعدّل PCB أو schematic أو firmware. النتائج أدناه تفصل بين قياس هندسي من الملفات، وتوصية، وما يحتاج اختبارًا على جهاز حقيقي. ملفات الأدلة بجوار هذا التقرير. بناءً على طلب المالك، جميع الملاحظات والتوصيات في هذا الملف فقط؛ تراجعت عن إضافاتي المؤقتة إلى وثائق المشروع. أرقام R تخص هذه المراجعة وحدها، وأرقام I تشير إلى سجل المشاكل الموجود مسبقًا.

## 1. النتائج الأهم

| الأولوية | النتيجة والأثر | الدليل | الإجراء المقترح |
|---|---|---|---|
| قبل طلب البوردة — R-01 | Layout دائرة LM5164 لا يحافظ على قرب الأجزاء الحرجة. أقرب مكثف سيراميك لدخل U601.2 يبعد 20.512 مم بين مراكز الأرجل، ومساره النحاسي 26.002 مم. مسار BST إلى C604 يبلغ 25.728 مم ويمر عبر طبقتين. خطر ضوضاء/ringing وعدم استقرار، وليس مجرد تجميل. | `pin-decoupling.json`، `pcb.json:pad_to_pad_distances`؛ `gen/place.py:167` يضع هذه القطع عبر pack في صفوف. TI LM5164 Rev D §7.4، ص23–25. | تحريك مكثفات الدخل والـbootstrap وFB/RON قرب أرجل U601، ثم إعادة توجيه المنطقة فقط. إعادة DRC وفحص المسارات الحرجة ومراجعة الصورة. |
| قبل طلب البوردة — R-02 | مكثفات فصل التغذية بعيدة عن العوازل والـADC. عند U405.1 أقرب مكثف مناسب على نفس التغذية والأرضي يبعد 29.367 مم؛ U404.1:‏ 19.031 مم. أقرب 100n مناسب لـU301.26:‏ 11.955 مم. وجود المكثف على نفس net لا يجعله محليًا. | `pin-decoupling.json`؛ `gen/place.py:86,106,122,124`. قياس PCB مباشر، مستقل عن ترشيح المحلل الآلي. | توزيع كل مكثف عند طرف التغذية المعني، مع مسار أرضي قصير وvia مناسب. مراجعة VCC/AVCC للـMCU أيضًا أثناء نفس التعديل. |
| قبل استخدام الجهاز — R-03 | charge pump يكشف توقف النبضات، لكنه لا يثبت أن البرنامج يواصل الفحص. Hardware PWM على OC0A يمكن أن يستمر أثناء تعليق الـmain loop. عبارة «hung firmware يفصل في 10–30 ms» أوسع مما تثبته الدائرة. | `gen/c_out.py:pump`، `0032` rev4؛ دليل ATmega1284P §16.7.3. البرنامج القديم يستخدم خرجًا ثابتًا وWDT=2s. | تعريف heartbeat مرتبط بتقدم الفحص والصلاحية، مع watchdog لا يُغذّى من ISR مستقلة عن سلامة التطبيق. اختبار تعليق loop مع استمرار timer/interrupts، وقياس زمن فتح الكونتاكت. |
| قبل استخدام الجهاز — R-04 | جدول «13 slots / 0.57s» لم يستوعب AVDD/6 كل scan، المضاف في rev3. البنود المسماة الآن تحتاج 14 conversion على الأقل إذا احتفظنا بها كلها في الدورة؛ PGA ratio قد يزيدها. | `0032` rev1–3، I-104؛ AD7124 Table 62؛ حسابات هذا التقرير، القسم 9. | جدول صريح لكل slot والـsetup/gain/filter والـdeadline. الحساب التمهيدي 0.624s للدورة، نحو 5s للـburnout و10s للدوران الكامل لفحص common-mode، قبل overhead. لا تعِد فحص 24 قناة بالتتابع بين البنوك الثلاثة. |
| قبل استخدام الجهاز — R-05 | بعض قواعد تشخيص الأعطال ستنتج إنذارات كاذبة: EMF سالب طبيعي عندما تكون الوصلة الساخنة أبرد من CJ. ADT7310 يعطي 0x0000 عند 0°C؛ ليس كل صفر انقطاع SPI. | `0032` rev3، I-104؛ ADT7310 ص13. استدلال حراري أساسي؛ لا يوجد driver جديد بعد. | إثبات الاتصال من ID/config/status/freshness، وعدم استخدام القيمة الخام وحدها لتشخيص الباص. فحص القطبية ضمن تشغيل معروف أو اختبار commissioning. |
| قبل اعتماد دقة القياس — R-08 | حساسات CJ ليست ملتصقة بالتوصيلات: أقرب pad يبعد 25.20–27.43 مم، والأبعد يصل 35.14 مم. تطابق حساسين مع بعض لا يثبت أن كليهما يساوي حرارة الوصلات. | `plane-cj-audit.json`؛ U102/103↔J101/102، U202/203↔J201/202، U302/303↔J301/302. | مراجعة موضع الوصلة المعدنية الفعلي في plug، ميزانية خطأ حراري، وتجربة تدرج حرارة مع LCD وRS485 والريلايات في أسوأ حالة. إن أمكن تحسين المواضع محليًا قبل التصنيع فالأفضل الآن. |
| قبل إصدار حزمة تصنيع — R-06 | 24ch بلا بوابة تحقق تحميه مثل 8ch: CI يفحص 8ch فقط؛ board_provenance مثبت على ملفات 8ch؛ fab.py يحفظ fills على المصدر، بلا lock/provenance gate، ويعيد استعمال مجلد اليوم نفسه. | `.github/workflows/hardware.yml`، `hardware/8ch/board_provenance.py:HERE/WATCHED`، `gen/fab.py:drc_ok/main`. | validate24 على snapshot، ورفض الكتابة مع lock أو تغيّر المصدر، وmanifest hashes، ومجلد إصدار فريد، وربط report وBOM/CPL/Gerber بنفس snapshot. |
| قبل اعتماد العرض والسعر — R-07 | BOM/CPL يمثلان القطع المركبة فقط، وليس طقم تركيب الجهاز. 6 plugs للقنوات وplug ENGINE REF موصوفة بالتعليقات لكنها ليست ضمن BOM. LCD والأزرار/المشغلات والمباعدات والفيوز والحامل والاختبار والطلاء ليست سعر $105. | `gen/c_bank.py` C14234، `gen/c_iso.py` C8466؛ `cost.csv`؛ `BOM-JLCPCB.csv`. | BOM منفصل للملحقات ضمن نفس الإصدار، وعرض NORI شامل ومحدد الاستثناءات. لا تضاف plugs غير المركبة إلى CPL. |
| قبل PCBA — R-09 | لا توجد fiducials محلية على البوردة رغم كثرة SMT ووجود LFCSP. قد يضيفها المصنع على panel، فلا أعتبر غيابها وحده عيبًا حتميًا. | PCB footprint inventory، FD-001. | توثيق طريقة المحاذاة/panel fiducials مع NORI، وإضافة علامات محلية إذا طلبها، قبل تثبيت ملفات التصنيع. |
| تنظيم التنفيذ — R-10 | المستندات تتحدث عن منتجات مختلفة: README وAGENTS يعتبران 8ch نشطًا؛ GOAL ما زال يذكر 3 modules وLCD خارجيًا؛ README24 يذكر مهام انتهت؛ 0032 رأسه proposed rev1 بينما به rev4. | الملفات نفسها مقارنة بقرارات 0031–0033 والشجرة الحالية. | تحديث نقاط الدخول وملخص المتطلبات الحالية، مع إبقاء تاريخ القرارات. فصل «مطلوب/مصمم/مُختبر» وعدم جعل نجاح build قديم علامة جاهزية الجديد. |

## 2. المعمارية: ما يستحق الإبقاء عليه

بوردة واحدة و3 ADCs اختيار معقول لـ24 قناة على موتور واحد؛ يقلل شبكة الوحدات والتغذية المتكررة. فصل جزيرة الحساسات عن الكنترول قرار مفيد. هو عزل مجموعة، ولا يحل اختلاف جهد كبير بين مجسات على ماكينات مختلفة. أتعامل مع قبول الجزيرة الواحدة وقيود الريلاي المسجلة كحدود المشروع الحالية، ولا أفتح إعادة تصميم عامة دون حاجة مثبتة.

ATmega1284P يوفر مساحة أوضح من ATmega32 للـ24 قناة والـdiagnostics والـUI. لا أرى من الشجرة سببًا مثبتًا يبرر الانتقال إلى STM32 أو إضافة RTOS الآن. التحدي هو برنامج محدد الزمن ومختبَر، لا عدد MHz وحده. هذا تقدير هندسي، وليس benchmark لتنفيذ 24ch لم يُكتب بعد.

قرارات جيدة قائمة: energised-to-run، ACK بعد بدء التشغيل أو trip، منع رفع limit قبل حفظه والتحقق منه، إخراج comms من قرار الحماية، bias كبير للـTC، REF مستقل للمقارنة، feed/sense للمرجع الأرضي، سجل issues/decisions، وفصل مصادر التصميم عن production.

المعمارية تحمل تعقيدًا مشروعًا لأن grounded/mixed probes وكابلات 50m ليست مسألة ADC فقط. لا أوصي الآن بإلغاء 20M أو الحماية أو المرجع المستقل لتوفير سنتات. في المقابل، عدد الحساسات CJ وطريقة عزل SPI والـRS485 هي مجالات توفير حقيقية في إصدار لاحق بعد إثبات القياس.

**حدود الحماية:** coil readback يراقب عقدة قيادة الملف، ولا يثبت انتقال الكونتاكت أو استمرارية الملف. قطبان على نفس الريلاي ليسا قناتي فصل مستقلتين؛ لا يصح تحويلهما إلى ضمان عام ضد welding/mechanical faults. I-081 مقبول كقيد سابق؛ المراجعة تصحح مدى الادعاء ولا تدّعي SIL/PL أو single-fault tolerance. كذلك SMBJ5.0A لا يصبح crowbar مضمونًا لحماية MCU لمجرد اسمه، وهو قيد سبق تسجيله في 0032 rev4.

## 3. البرنامج وطريقة تنفيذه بسهولة

الموجود فعليًا هو `MCU := atmega32`، MAX31856/MAX6675، ثماني قنوات، limit مشترك، LCD 16×2، وخرج RUN ثابت. لا يوجد target AD7124/ATmega1284P جاهز. لذلك العمل المتبقي **port وتطوير وظيفي معتبر**، وليس تغيير 8 إلى 24 في define.

طبقات app / HAL / MCAL مفيدة والملفات الحالية محدودة الحجم؛ أكبر ملف جديد للـgenerator هو maze.py بـ477 سطرًا. يحتفظ المشروع بالمنطق القابل لإعادة الاستخدام، مع BSP/target واضح للـ24ch. لا داعي لنسخ firmware كاملًا أو خلط pin maps القديمة والجديدة بـifdef موزع في كل مكان.

التقسيم المقترح: driver AD7124، driver CJ، scheduler للبنوك الثلاثة، حالة مستقلة لكل قناة تشمل timestamp/validity/faults، منطق trip/ACK، تخزين إعدادات versioned، واجهة عرض، وModbus منخفض الأولوية. هذا توصية، لا قرار تنفيذ تم تطبيقه.

يُختبر scheduler قبل التجميل: قراءة حديثة لقناة ساخنة يجب أن تُقيّم فورًا؛ تأخير القرار لنهاية sweep إضافية قد يستهلك هامش الثانية. توثيق مهلات SPI/ADC والـdiagnostics وEEPROM وLCD مهم. الـwatchdog يراقب تقدم المسار المطلوب للحماية، لا مجرد أن loop أو interrupt تدور.

EEPROM الحالية تستخدم record واحدًا وCRC/readback؛ بنية سليمة كبداية لكنها ليست إعدادات 24 قناة. يلزم schema/version واضح وقيم كل قناة وopen-circuit action، مع اختبار انقطاع الكهرباء أثناء save. سجلا A/B مع sequence وCRC خيار عملي لاسترجاع آخر إعداد سليم؛ فائدته أكبر من تعقيد UI مبكرًا.

الاختبارات الضرورية: قناة واحدة ساخنة في كل موضع من الـ24، SPI stuck/CRC/ID خاطئ/reset converter، عينة قديمة، فقد CJ، فقد REF، save منقطع، ACK مع fault أو سخونة، ثبات PWM أثناء hang، reset/brownout، ورسائل Modbus متواصلة. اختبارات الـ8ch الحالية لا تغطي هذه النسخة. لا تُنقل فرضية «ثبات 0.1°C لمدة 55s = حساس معطل» تلقائيًا؛ I-098 ما زال صحيحًا.

### 3.1 تفاصيل إضافية من مراجعة مسار البرنامج والتسليم

**R-11 — أداة البرمجة لم تنتقل إلى اللوحة الجديدة (مؤكد من المصدر؛ قبل commissioning).** `firmware/program.ps1` يختار `-p m32`، ويقبل افتراضيًا اسم `thermo_8ch_max31856.hex`، ويفحص low/high fuses الخاصة بالـATmega32A. `fuses.md` لنفس المعالج القديم. هذا ليس مسار برمجة ATmega1284P؛ لا يُستخدم خيار تجاوز اسم الصورة لإجباره على النسخة الجديدة. المطلوب profile مستقل للـ24ch يحدد المعالج والساعة وكل fuse مطلوب من دليل المعالج الفعلي، بما يشمل BOD/JTAG/WDTON، مع readback وسجل رقم الجهاز ونسخة البرنامج وhash الصورة. أرقام fuse القديمة ليست اقتراحًا للمعالج الجديد. لم أوصل programmer أو أغيّر أي fuse.

فحص اسم ملف HEX الحالي يمنع الاختيار الخطأ الشائع، لكنه لا يثبت محتواه: ملف آخر أعيدت تسميته إلى الاسم المقبول يمر بشرط الاسم. توصية إصدار الـ24ch: manifest يولده build مع board target وMCU وhash، ويقارنه برنامج التحميل بالمحتوى قبل الكتابة؛ لا يلزم نظام توقيع معقد لمجرد حل خلط الصور محليًا. ينبغي إبقاء فحص توقيع المعالج فعالًا.

**R-12 — معنى PASS محدود بما تمثله الاختبارات (مؤكد من المصدر).** integration test يشغّل `main_8ch.c` الحقيقي، وهذه نقطة قوة. لكنه يستبدل `hal_run_permit_readback_agrees()` بإرجاع true دائمًا (`tests/test_app_integration.c:84`)، ويستبدل تخزين EEPROM بدالة اختبار؛ watchdog في `tests/host_mocks/avr/wdt.h` عبارة عن no-op. `host_delay_ms()` يعد دورات loop ولا يحاكي أزمنة كل HAL call. لذلك PASS لا يثبت زمن الفصل الحقيقي، ولا feedback mismatch في مسار main المتكامل، ولا تحمل EEPROM لانقطاع الكهرباء. اختبارات الوحدات قد تختبر منطق الأعطال منفردًا؛ هذا لا يغني عن السيناريو المتكامل. أضف حالات readback متعطل ومهلات متجاوزة إلى الاختبارات، وقِس WDT/PWM/relay على العتاد.

**تفاصيل port مؤكدة، وليست أعطالًا إضافية في منتج 8ch:** `protection.c:40,277,359,397` يطبع رقم القناة بحرف `'1' + index`؛ عند index=9 تصبح ':' بدل CH10. يلزم تنسيق عشري بعرض كافٍ في شاشة 20×4 وفي رسائل رفض ACK. `hal_temperature_sample_t` يحتوي حرارة وfaults وvalid فقط، بلا timestamp؛ توسيع العدد وحده لا يضيف اكتشاف العينات القديمة. بايت faults مستخدم بالكامل بثمانية flags، ولذلك يجب اختيار تمثيل واضح للتشخيصات الجديدة دون تداخل bits أو إسقاط سبب العطل. لا أنصح باستبدال كل الكود: احتفظ بوظائف اللاتش والـACK القابلة للاختبار، وعدّل عقود البيانات والعرض وحدود كل قناة.

**تحسين قابلية الاستخدام:** شاشة العطل يجب أن تبيّن القناة 01–24 وسبب المنع الفعلي، وتحتفظ بسبب الفصل الأول مع إظهار الأعطال الحالية. هذه توصية لمواصفات الـ24ch، لا ادعاء أنها منفذة. حدّد سلوك زر ACK المطوّل أو العالق، ورفض ACK مع بيانات غير حديثة، وفصل تعديل setpoint المرشح عن القيمة النشطة حتى نجاح الحفظ. المنطق الحالي لفصل candidate/active مفيد ويستحق النقل مع اختبارات regression.

## 4. القياس والطاقة والـPCB

توصيل AD7124 الثلاثة إلى AIN pairs، references منفصلة، REGCAPA/D وEP، وADT7310 pin maps متسق مع المخططات ومع جداول المصنع التي راجعتها. اتجاهات ISO7761 تسمح بالـCS/SPI والـREFOK، وتغيير levels يتم بواسطة تغذيتي العازل؛ إنذارات 5V→3.3V العامة ليست خطأ توصيل هنا.

مدخل 2.2k + clamp + 1k موجود؛ لكنه ليس اعتمادًا لتحمل pulse محدد. MPN مقاومة الدخل عادية وتعليقها يقول pulse rating to verify. الـwashing/coating وقياس التسرب I-105 ضروريان. وجدت شبكة V_BIAS ومساراتها، لكن لم أثبت guard فعالًا حول كل clamp/R2/AIN؛ لا أغلق هذا البند لمجرد وجود net باسم V_BIAS أو إرجاع Ccm إليها.

الحساب المجمع الأحدث للطاقة في CALCULATIONS §7.7 يصل إلى نحو 0.449A على 5V تحت افتراض LCD/R502 الحالية، وحوالي 23% هامش hold للفيوز عند نقطة 9V/70°C المذكورة. هذه **screening assumptions**، ليست مواصفة مضمونة للموديول YLPTEC أو الـLCD غير المختار. لا تنقل مواصفات MORNSUN تلقائيًا إلى YLPTEC. القياس عند startup/idle/RUN/cranking ومراجعة الفيوز/TVS والطاقة الحرارية ما زالت مطلوبة.

شكل البوردة 170×145، أربع طبقات، 462 footprint، 4581 track segment و589 via. 441 designator قابلًا للتجميع في BOM/CPL، والباقي holes/test points. كلا الملفين يحتوي نفس designators، بلا orphan. ليست 462 قطعة يجب شراؤها.

In1 أرضي الجزيرة وIn2 تغذيتها لهما كل منهما **filled outline واحد متصل** في المصدر المحفوظ. المسارات الداخلية الإضافية تخص TC21_PA وCS_CJ5_ISO فقط. لا أطلب إلغاءها لمجرد أنها inner-layer؛ وجودها لا يقطع plane إلى جزيرتين حسب استخراج pcbnew. توجد ثقوب antipad طبيعية ولا تعني أن النحاس «مصمت في كل نقطة».

TC21_PA طوله 17.657 مم، وNA طوله 32.627 مم. فرق الطول لا يستلزم delay matching لإشارة الحرارة البطيئة، لكنه يترك التقاط ضوضاء غير متناظر يحتاج اختبارًا. SCLK_ISO إجمالي فروعه نحو 280 مم و16 via؛ زمن rise/fall والـringing مهمان حتى لو SPI بطيء. راجع waveform عند أبعد ADC وCJ، مع الرنين/overshoot وحدود المنطق؛ لا تعتمد على تردد SPI وحده.

التجميع: NORI يحتاج تأكيد stencil/EP via treatment والتنظيف والطلاء وvia spacing. نقل vias خارج paste يقلل خطر سحب اللحام لكنه لا يثبت جودة لحام EP. عدم وجود X-ray يزيد قيمة اختبار bring-up والضوضاء لكل ADC، ولا يُعوَّض بعبارة DRC clean. يجب فحص اتجاهات القطع في معاينة التجميع، وعدم افتراض أن دوران KiCad هو دوران ماكينة NORI تلقائيًا.

الميكانيكا ما زالت غير مغلقة: LCD exact drawing، buttons/actuators وارتفاعها، الوصول للـACK، عزل مسامير جزيرة الحساسات، ومساحة أدوات ربط الـplugs. وسوم التوصيلات موجودة، لكن قابلية قراءتها بعد تركيب الـplug والـLCD تحتاج نموذجًا أو طباعة 1:1 وتجربة فعلية.

## 5. السعر والقرار الاقتصادي

هذه ليست quotation شراء. `cost.csv` يجمع أسعار مصدر ثانوي jlcsearch، وليس تعهد توريد من NORI. مجموعه الدقيق $104.9148 لعدد 436 قطعة مسعّرة. خمس أزرار بلا سعر/MPN؛ إجمالي القطع المركبة 441.

| البند | التقدير المسجل لكل بوردة |
|---|---:|
| 6× ADT7310 | $32.427 |
| 3× AD7124-8 | $30.001 |
| 3× ISO7761 | $8.766 |
| ADM2587E | $7.645 |
| ATmega1284P | $5.868 |
| بقية القطع المسعّرة | نحو $20.21 |
| مجموع القطع المسعّرة | نحو $104.91 |

عرض PCB المسجل في 0033: خمس لوحات 8,710 جنيه = 1,742/لوحة؛ عشر لوحات 11,500 جنيه = 1,150/لوحة. **هذه أسعار PCB عارية مسجلة في المشروع**، لا تأكيد جديد من NORI، ولا تشمل بقية الجهاز. لم أخلط الدولار بالجنيه بسعر صرف مفترض.

السعر الكامل = PCB + المكونات بكميات الطلب الفعلية + assembly/setup + LCD/ميكانيكا/ملحقات + cleaning/coating + برمجة واختبار ومعايرة + تسليم وأي ضرائب/هامش واردة بعرض NORI. مسؤولية الاستيراد المسجلة على NORI لا تعني أن كلفتها صفر. مبلغ $156 للـ52 extended codes **افتراض JLC-style**؛ لا يصح تحميله على عرض NORI كأنه فاتورة مؤكدة.

راجعت أهم بديل سعرًا على LCSC: ADT7310 C578060 ظهر بسعر $5.4253 للواحدة و$4.1352 عند 30؛ TMP117 C699536 بسعر $1.0278 و$0.7831 عند 30. استبدال ستة يعطي فرق قطع تقريبي $26.38 عند qty1، أو $20.11 عند qty30. لكنه ليس drop-in: I²C، addressing لست حساسات، عزل الباص، layout وبرنامج جديد، وWSON أصغر يحتاج تجميعًا مناسبًا. هذه أرقام صفحات وقت المراجعة، لا stock reservation أو اعتماد للبديل.

**التوصية الاقتصادية:** لدفعة إثبات صغيرة، أصلح التصميم الحالي بدل تغيير واجهة القياس كلها بهدف توفير نحو $20/لوحة. عدد التعادل = كلفة التطوير/إعادة التأهيل الإضافية ÷ التوفير الصافي لكل لوحة. لا توجد بيانات أجور/كميات تسمح بإعطاء break-even رقمي صادق. بعد إثبات القياس، يدرس إصدار أقل كلفة: CJ أرخص، عدد CJ أقل فقط مع خريطة حرارة، أو RS485 اختياري إذا لم يكن مطلوبًا. تقليل المكثفات/الحماية الحساسة توفير ضعيف مقابل احتمال إعادة تصنيع كاملة.

## 6. بنية الملفات والتوثيق والنظام

التقسيم الرئيسي جيد: hardware بحسب الإصدار، firmware، docs، production. تقسيم generator إلى c_bank/c_iso/c_power/c_mcu/c_out واضح وأسهل من ملف واحد ضخم. المشكلة ليست عدد الملفات؛ المشكلة أن تعريف «المنتج الحالي» وبوابات التحقق لم ينتقلا مع انتقال الهاردوير.

أحتفظ بـhardware/8ch كمرجع دون نقل جماعي يكسر مساراته، وأصحح entry points إلى hardware/24ch. عند اعتماد نتائج المراجعة لاحقًا، أوصي بنقل البنود المقبولة إلى STATE/ISSUES؛ لم أفعل ذلك تنفيذًا لطلب المالك إبقاء المراجعة منفصلة. أستبدل تراكم التعليمات المتعارضة بملخص current specification واحد يشير إلى ADRs، وتبقى revisions السابقة للتاريخ. مستند GOAL مملوك للمستخدم؛ سجلت التعارض ولم أغيّر متطلباته نيابةً عنه.

المطلوب في workflow: hardware24 validation منفصل يحمي المصدر، فحص model↔schematic↔PCB↔BOM، تحقق MPN/package للقائمة الفعلية، ثم إصدار immutable مربوط بالـcommit وحالات dirty tree والـhashes. production يُتجاهل في Git وهذا مناسب للمخرجات المتجددة، لكن الحزمة المطلوبة فعليًا يجب أرشفتها حسب سياسة المشروع؛ القاعدة الحالية للأرشفة تذكر 8ch وحده وتحتاج تعميمًا.

إصلاح مصدر تكرار المشكلة: `pack()` العام يصلح لترتيب قطع غير حساسة؛ buck/decoupling/crystal/CJ تحتاج constraints كهربائية وحرارية موثقة، لا مجرد courtyard بلا overlap. ووضع Locked كان مفيدًا لحماية مسارات مكتملة، لكنه يمنع Shove عند الإنهاء؛ الدرس مسجل في TOOLS ولا يحتاج أداة جديدة.

## 7. ما اختُبر فعلًا وما لم يثبت

| الفحص | النتيجة / حدود الثقة |
|---|---|
| ERC24 جديد | 0 errors / 0 warnings، 12 sheets؛ `erc24.rpt`. توجد فئات ignored مذكورة داخل التقرير. |
| DRC24 جديد، refill في الذاكرة وschematic parity | 0 errors، 3 track_dangling warnings، 0 unconnected، 0 footprint errors؛ `drc24.rpt`. لا exclusions فردية في project. |
| 8ch snapshot validation | PASS؛ ERC/DRC 0/0، netlist مطابق 202 components/163 nets/647 pins، 129 passives مطابقة. `production/validation-20261009-113815-e0d952/`. |
| firmware/build.ps1 | 4 images بُنيت، 3 suites PASS؛ `firmware-build.txt`. كلها targets قديمة. |
| schematic analyzer | 462 non-power components /296 nets، 191 findings خام. العدد يطابق PCB؛ 10 voltage-domain errors أُسقطت بعد فحص تغذيات العوازل. |
| PCB analyzer --full | 99 findings خام؛ تم فحص الأرقام المؤثرة بـpcbnew مستقلًا. |
| cross_analysis | تحذير plane split واحد؛ لم يتأكد عند فحص filled polygons، ولذلك لا أعتمده كقطع تغذية. |
| EMC analyzer | 265 finding في 8 فئات؛ نتيجة 0/100 **ليست شهادة فشل EMC**. كثير منها لا يفهم الجزر أو thermal/TC nets. Layout التغذية البعيد مثبت مستقلاً؛ الباقي test plan ومراجعة انتقائية. |
| thermal analyzer | حلّل عنصرين فقط عند 25°C؛ 5 معلومات، بلا warnings. درجة 100/100 لا تؤهل جهازًا في لوحة ساخنة ولا تقيس خطأ CJ. |
| Gerber analyzer | 11 ملفات Gerber وملف drill، بلا findings آلية؛ لا اعتماد CAM/stencil/rotation من المصنع. |
| مطابقة BOM/CPL | 93 lines /441 designators لكل منهما؛ الاختلاف في المجموعتين صفر. |
| datasheets | sync عام حاول 88 part وفشل تحميلها؛ fallback جلب 7 PDFs من المصنع، مع PDFs محلية وقراءة ADI عبر الويب. سجل الأخطاء محفوظ. لا أعتبر كل BOM موثقًا أو كل footprint مؤهلًا. |
| SPICE | لم يُنفذ: لا ngspice/LTspice/Xyce executable متاح؛ KiCad library ليست CLI simulation run. لم أستبدله بادعاء أن حسابًا يدويًا simulation. |
| lifecycle | 75 MPN جميعها unknown، وsources_available فارغ؛ لا إثبات active أو discontinued. الأدلة في `lifecycle.json` و`lifecycle.log`. |

**تغطية pin verification:** جداول AD7124 ص15–17 وADT7310 ص6، MCU package/pin multiplexing، ISO7761 directions/supplies، TLV7031، TL431 TI DBZ، LP2985، وBAV199/BAT54S روجعت مع connectivity المستخرجة. أسماء القطع/اتجاهاتها وحدها ليست فحص تحمل نبضات أو حدود حرارية. لم أعد تأهيل رسم الشركة المصنّعة لكل connector/relay/module/LED/crystal، ولا package/rotation لكل line من الـ93؛ هذه فجوة إصدار واضحة، خصوصًا YLPTEC والريلاي وأزرار بلا MPN. المقاومات والمكثفات الثنائية لا تحتاج pinout direction لكن تحتاج rating/derating وتحقق MPN؛ ليست كلها manufacturer-verified في هذه الجولة.

**False positives:** العوازل تمر فوق barrier عمدًا والـkeepout يسمح بالـfootprints/pads؛ لا أنقل KO-001 كخطأ. الموصلات على الحافة عمدًا، فـ0.1mm courtyard-to-edge ليس pad clearance violation. thermal via minima العامة للـADC ليست دليل أنه يسخن؛ ترتيب paste/tenting هو السؤال التصنيعي. SK-001 على F601 لم يؤكده DRC. بعض «decoupling» التي عدّها المحلل C213/C223 هي TC filters أصلًا؛ لهذا استخدمت rail+ground pin audit بدل الاعتماد على ترتيب أقرب قطعة. أرقام GP-001 التي تعتمد opposite outer layer لا تثبت غياب In1 المرجعي.

**التغير عن المراجعات السابقة:** توصيلات الإنهاء الثلاثة القديمة أصبحت مكتملة، ووضعت inner routes بقرار0033. silkscreen وEP via/paste تعديلات موجودة، وBOM/CPL جديدان. ملاحظات prototype grounding/leakage/mechanics/firmware ما زالت قائمة. عيوب قرب bypass/buck المسجلة هنا لم تُكشف بنجاح ERC/DRC السابق؛ لا يُنسب لها اجتياز لم يحدث.

## 8. ترتيب العمل الأقل إعادةً وتكلفة

1. اعتماد error/temperature/ambient/transient/latency envelope وجدول الفحص، وتصحيح قواعد التشخيص والـheartbeat قبل كتابة driver كامل.
2. إصلاح محلي لـbuck ثم decoupling، ومراجعة CJ/guards والميكانيكا في نفس دورة التعديل. لا تعِد route البوردة كلها ولا تشغّل place.py فوق المسارات الحالية.
3. بوابة validate24 وrelease manifest، وتأكيد parts/ملحقات/stencil/coating/fiducials مع NORI. إغلاق open ordering items وإعادة إنتاج الحزمة من snapshot واحد.
4. target24 وبرنامج bring-up واختبارات host، ثم نموذج على الطاولة قبل أي استخدام للحماية. Firmware العمل الأساسي يمكن أن يتقدم بالتوازي زمنيًا مع التصنيع بعد تثبيت pin map، دون كاتب ثانٍ على PCB.
5. اختبار كل قناة، الأرضي المختلط، 50m cable/noise، gradient/humidity، fault injection وcontact timing. ثم تجربة ميدانية مضبوطة وفق متطلبات الموقع.
6. تحسين التكلفة بعد نتائج النموذج وعرض NORI الحقيقي. لا أضع نسبة إنجاز أو موعدًا من شكل routing؛ الاختبار والبرنامج يمثلان عملًا أساسيًا متبقيًا.

## 9. حسابات المراجعة القابلة للتتبع — 2026-10-09

**Schedule, not a firmware timing qualification.** The named rev2 slots are
8 TC + burnout + external-reference comparison + zero + nonzero + rotating
common-mode = 13. Rev3 additionally requires AVDD/6 every scan. Retaining
all these tasks needs at least 14 conversion slots; extra gain-ratio tests,
switching/recovery and software overhead are not included below.
Input: AD7124-8 Rev F Table 62, p64, mid-power post-filter 25 SPS settling
42.331 ms; retain the earlier screening assumption of a -5% clock.

    slot screening = 42.331 / 0.95 = 44.559 ms
    14-slot cycle = 14 x 44.559 = 623.825 ms
    one burnout channel per cycle, eight channels = 8 x 623.825 = 4.991 s
    one CM input per cycle, sixteen inputs = 16 x 623.825 = 9.981 s

Verdict: the repeated 13-slot/0.57s/approximately-4s claim does not include
all the later requirements. This is a lower-bound schedule with a clock
allowance, not an upper-bound trip latency. Evaluate each fresh TC result
promptly, keep three banks concurrent, and specify/measure all deadlines.
Source: https://www.analog.com/media/en/technical-documentation/data-sheets/ad7124-8.pdf

**Complete-device cost is not known.** Sum of existing `24ch/output/cost.csv`:

    sum(qty x unit_usd) = $104.9148 for 436 priced mounted parts
    mounted BOM/CPL = 441 refs; missing prices = five unselected switches
    recorded bare-PCB quote: 8710/5 = EGP1742; 11500/10 = EGP1150 per board

These exclude off-board plugs/LCD/mechanics, assembly/test/coating and
other quotation terms. NORI figures are recorded in 0033, not independently
re-quoted. Do not add JLC extended-part fees to NORI's price without its quote.

LCSC pages checked 2026-10-09: ADT7310 C578060 $5.4253 at 1+ / $4.1352 at 30+;
TMP117 C699536 $1.0278 at 1+ / $0.7831 at 30+. Hypothetical six-part replacement:

    qty1 saving = 6 x (5.4253 - 1.0278) = $26.385 / board
    qty30 saving = 6 x (4.1352 - 0.7831) = $20.1126 / board
    break-even board count = additional engineering/qualification cost
                             / net per-board saving

Not a selected substitution: bus/addressing/isolation, footprint, software
and test changes must be costed. Sources: https://www.lcsc.com/product-detail/C578060.html
and https://www.lcsc.com/product-detail/C699536.html .

**CJ geometry, not thermal error:** sensor footprint origin to assigned
header pad centre, sqrt((xs-xp)^2 + (ys-yp)^2), all in mm. Across six sensors,
nearest pad = 25.20-27.43 mm; maximum farthest pad = 35.14 mm. The physical
plug's metal junction location is not specified by pad centres. Evidence:
`production/review-20261009-system/plane-cj-audit.json` and its read-only script.
No temperature error is inferred from distance alone; R-08 requires a test.


## المصادر الخارجية المستخدمة

- [TI LM5164، layout §7.4](https://www.ti.com/lit/ds/symlink/lm5164.pdf)
- [TI ISO7761، التغذيات وlayout](https://www.ti.com/lit/ds/symlink/iso7761.pdf)
- [ADI AD7124-8، pin tables وTable 62](https://www.analog.com/media/en/technical-documentation/data-sheets/ad7124-8.pdf)
- [ADI ADT7310، pin table وتمثيل الحرارة](https://www.analog.com/media/en/technical-documentation/data-sheets/ADT7310.pdf)
- [Microchip ATmega1284P، timers/watchdog](https://ww1.microchip.com/downloads/en/DeviceDoc/Atmel-42719-ATmega1284P_Datasheet.pdf)
- [LCSC ADT7310 C578060](https://www.lcsc.com/product-detail/C578060.html)، [TMP117 C699536](https://www.lcsc.com/product-detail/C699536.html)


## 10. مراجعة إضافية: هل يستطيع فريق الشركة تركيبه وتشغيله دون شرح متكرر؟

**الحكم العملي:** الجهاز يمكن أن تكون واجهته عادية: 24 مدخل حرارة، تغذية، contact للسماح بالتشغيل، alarm، وRS-485. لكن المشروع الحالي لم يتحول بعد إلى «منتج يُركّب من ورقة توصيل». أكثر نقطة تحتاج عناية هي ENGINE REF ذو السلكين، ثم اختيار طرف الكونتاكت، ومكان الشاشة والأزرار، وربط أرقام القنوات بأماكنها الحقيقية. التعقيد الداخلي المقبول ليس مبررًا لتحميل الفني تفاصيل ADC والـbias والـcharge pump.

هذه الإضافة تستخدم أفكار `review-workspace/references/testing-ideas.md` عن اختبارات قابلة للإعادة ومصفوفة المتطلبات. Thermo مشروع تطوير خاص بالمالك؛ لم أطبق هيكل received/work الخاص بمراجعة مورد، ولم أضف نظام وثائق جديدًا للمشروع.

### 10.1 نقاط قد تسبب أخطاء تركيب فعلية

**R-14 — ENGINE REF ليس طرف أرضي عادي (SRC مؤكد، وسيناريو الالتباس استنتاج).** `gen/c_iso.py:99–102` يعرّف J401.1=FEED وJ401.2=SENSE، ويطلب سلكين يلتقيان عند جسم المحرك فقط. هذا أدق من وصف «سلك مرجع» بالمفرد في بعض الوثائق. لا يُوصلان كجمبر عند البوردة؛ فهذا قد يعطي مسار feed→sense دون إثبات وصولهما إلى المحرك. اختبار Q401 يختبر استجابة دائرة sense، ولا يثبت بمفرده مكان التقاء السلكين. هذا استنتاج من التوصيل وليس عطلًا ميدانيًا جرى قياسه. المطلوب رسم توصيل واحد وحزمة سلكين مرقمة من المصنع، ونقطة ربط محرك محددة، واختبار قطع كل سلك منفردًا مع grounded/insulated/mixed probes. لا يُختزل هذا الطرف إلى SH أو 0V أو PE ولا يوصف كتأريض حماية.

**R-15 — اسم TRIP وحده قد يقود لاختيار NC (SRC مؤكد، احتمال الخطأ بشري).** المخطط يعطي J701.1=COM، .2=NO، .3=NC. مسار السماح بالتشغيل المقصود COM→NO يغلق عند energised-to-run ويفتح عند فقد القدرة؛ كلمة «TRIP» لا تعني أن NC هو طرف الفصل الصحيح. الـNC الموجود من قطب واحد ليس مسار الـNO ذي القطبين على التوالي. يجب أن يكون رسم الموقع صريحًا: أي terminal يدخل في دائرة السماح، وحالة الكونتاكت عند power-off/startup/healthy/tripped. إذا كان مدخل الماكينة له منطق مختلف، يحسمه رسم الربط الفعلي، ولا يختار الفني طرفًا بالتخمين. تحقق القبول بقياس الكونتاكت نفسه، لا LED RUN وحده.

| الواجهة الفعلية | ما يجب أن يفهمه الفني من ورقة التركيب | اختبار الاستلام |
|---|---|---|
| J601: +24V / 0V / CHASSIS، بينما silk يسمي الثالث SH | feed من البطارية عبر الفيوز الخارجي المختار؛ تمييز chassis عن 0V وعن engine reference | قياس الجهد والقطبية قبل التوصيل، ومطابقة نقطة chassis بالرسم |
| 24 زوج K+/K− على ستة plugs | CH01–CH24 مع اسم الموقع ونوع كابل K/extension المعتمد؛ لا استبدال امتداد K بسلك نحاس عادي بلا تحليل موضع CJ | إثارة حرارية/محاكي مستقل لكل موقع، والتحقق من رقم القناة والقطبية |
| J401 FEED / SENSE | سلكان إلى نقطة المحرك المحددة؛ لا جمبـر عند اللوحة | قطع كل سلك والتأكد من الإنذار/المنع طبقًا للمواصفة |
| J701 COM/NO/NC | contact للسماح، signal load ≤30VDC/1A بحسب التصميم؛ لا يوصل مباشرة بحمل غير موثق | power-off، startup، ACK، trip، وإعادة القدرة مع قياس contact |
| J702 alarm | حالة warning المتفق عليها، مستقلة عن trip؛ تحديد ما يحدث عند فقد قدرة الجهاز | warning ثم power loss، ومقارنة indication المحلية والبعيدة |
| J703 A/B/GND وTERM/BIAS jumpers | رسم RS-485 يحدد الطرفين والـtermination والـbias؛ shield عند البار المقرر | comms صحيحة ثم فصل الكابل/زحام الرسائل دون تعطيل الحماية |

المواضع مؤيدة بالموديلات `c_power.py/c_bank.py/c_iso.py/c_out.py` ووسوم `silk.py`. هذه ورقة مراجعة واجهات، **ليست رسم تركيب موقع معتمدًا**؛ مسارات الكابلات، load الماكينة، الفيوز، القطاعات، الطرفيات والميكانيكا لم تُحسم كلها.

الـplugs الستة المتشابهة تسمح بخطأ ربط مجموعات قنوات يعطي درجات معقولة على أسماء خاطئة؛ diagnostics الكهربائية لا تثبت اسم الأسطوانة. أوصي بترقيم ظاهر على جانبي كل plug، وجدول CH↔الموقع في commissioning، ووسيلة منع التبديل إن كانت متاحة بالمكونات الحالية. لا أعتمد لون سلك K وحده دون تسمية معيار الكابل، ولا أضع ألوانًا مفترضة في الرسم.

الـCJ يقيس حرارة منطقة تحول أسلاك thermocouple إلى معدن التوصيلات؛ ترتيب الوصلات والـplug وحرارة اللوحة جزء من دقة الجهاز. أي intermediate terminals أو وصل نحاس في الطريق يحتاج مراجعة تعويض/تدرج حراري. لا يعني ذلك أن كل connector نحاسي ممنوع، بل أن الوصلات وحرارتها لا تُترك مجهولة. هذا متسق مع شرح [NI عن CJC عند terminal block](https://knowledge.ni.com/KnowledgeArticleDetails?id=kA00Z000000PA6KSAW&l=en-GB).

### 10.2 أبسط تشغيل وصيانة مقترحين

الشاشة الأساسية: اسم/رقم القناة، الحرارة، limit، والحالة. عند trip: السبب والقناة أولًا؛ لا تترك الرسالة مخفية وراء menu أو auto-page. ACK يقر العطل بعد زوال سبب المنع ووجود قراءات حديثة، ولا يغير setpoints. SET/ESC لهما سلوك ثابت واضح، والـcandidate لا يصبح active إلا بعد حفظ ناجح. لا أسماء REFTEST وCRC وPGA في مسار التشغيل العادي؛ تظهر كأكواد خدمة ذات معنى في دليل الصيانة.

خيارات المصنع ليست خيارات المشغل: عدد القنوات المطلوبة 8/24، نوع اللوحة، calibration coefficients، وجدول التشخيص لا تتغير من قائمة عادية. limit كل قناة يضبطه المخول بالتشغيل. default لفقد الحساس يجب أن يكون واحدًا ومعلنًا؛ الوثائق الحالية بين «لم يُحسم» في 0031 وdefault trip في I-104 وalarm-only قابل للضبط. **R-16 — هذا تضارب مواصفة تشغيل يجب حسمه قبل الاختبار، وليس سببًا لاختراع عدة modes إضافية.** أوصي بأن يكون trip هو الافتراضي الآمن، وأي استثناء معتمد يظهر بوضوح ويُختبر؛ القرار النهائي يتبع متطلبات الموقع والمالك.

الشاشة والأزرار داخل اللوحة بموجب 0031. قبول فتح الباب للرؤية والـACK ما زال سؤالًا مفتوحًا بالمشروع؛ إذن لا يصح وصف HMI بأنه سهل التشغيل قبل تجربة الوصول والرؤية بالفعل. اختبار ورقي/نموذج 1:1: فني آخر يركب الـLCD، يصل إلى كل screw، يبدل plug ويضغط ACK بالقفاز إن كان مستخدمًا، دون فك اللوحة أو شد الكابلات. لا أقترح تعديل الباب أو HMI جديدًا تلقائيًا.

الصيانة المقترحة على مستوى **تبديل وحدة كاملة** مع نسخة إعدادات معتمدة واختبار القنوات والكونتاكت، لا أن يُطلب من فني الموقع إصلاح bias أو LFCSP. احتفظ بوحدة spare مهيأة وبورقة calibration/limits مرتبطة برقمها. تكلفة spare واختبارها جزء من كلفة النظام، وليست تعقيدًا في الدائرة.

### 10.3 ما أبقيه وما أبسطه في المعمارية

| العنصر | الحكم ولماذا |
|---|---|
| لوحة واحدة و3 ADC تعمل بالتوازي | أبقيه؛ يزيل master/inter-module wiring ويخدم هدف 24 قناة. لا إعادة تقسيم دون سبب جديد |
| MCU واحد، trip محلي، RS-485 خارج قرار السماح | أبقيه؛ لا PLC أو cloud مطلوب لتشغيل الحماية |
| مرجع المحرك وحماية/تشخيص المدخل المختلط | مبرران وظيفيًا، لكن تأهيلهما يحتاج اختبارًا واضحًا وتسليم wiring محددًا؛ لا إزالة بهدف «تبسيط الشكل» |
| تشخيصات gain/ref/burnout الكثيرة | لكل تشخيص عطل مستهدف ووقت وحدود استجابة؛ إن لم يمكن إثبات فائدته وحدوده، تراجع صياغته بدل إضافة شرط عشوائي يسبب nuisance trips |
| heartbeat/WDT | أبقي الوظيفة وأحدد ارتباطها بتقدم الفحص؛ لا وعد أن PWM وحده يثبت حياة البرنامج |
| 8ch partly fitted والـlegacy images | أخّر اعتماد variant جديد حتى يثبت 24ch؛ أبق المرجع القديم واضحًا ومنفصلًا، دون حذف ضروري الآن |
| محركات routing مخصصة ومشاريع محاكاة متعددة | أدوات تطوير داخلية؛ لا تصبح شرطًا لتشغيل الجهاز أو صيانته أو شرح تركيبه |
| اختيار AVR بدل معالج أكبر/RTOS | لا دليل حالي يفرض تغييره؛ الأداء يُثبت باختبار target24. نقل المنصة الآن يزيد عملًا قبل حل المخاطر المقاسة |

الجهاز custom ليس بالضرورة الأرخص للشركة لمجرد أن BOM رخيص. المقارنة الصحيحة مع وحدة جاهزة أو حل مألوف لدى فريقها تشمل التطوير والتأهيل وspares والتدريب والتوقف. لم أحصل على عرض بديل مكافئ أو تكلفة ساعات الفريق؛ لذلك لا أدعي وفرًا كليًا مثبتًا. التوصية الحالية: إثبات نموذج صغير قابل للتسليم والصيانة قبل توسيع التصنيع، مع إبقاء مقارنة الشراء الجاهز خيارًا اقتصاديًا إذا عجزت الشركة عن امتلاك صيانة المنتج.

## 11. اختبارات جديدة نُفذت في هذه الإضافة

كل التجارب في `extended/` بجوار التقرير. لم أشغل board generator ولم أبرمج عتادًا. المصدر المستخدم هو نفسه؛ التغييرات المتعمدة للأخطاء كانت على نسخ مؤقتة فقط.

| الاختبار | النتيجة | الدليل والحدود |
|---|---|---|
| exhaustive host checks لمنطق protection/settings | **passed: 1,114,184 checks، صفر failures** | `extended/baseline.log` و`protection_properties.c`. جميع قيم int16 لحرارة قناة واحدة، في كل موضع من 8، مع threshold=900 وreset=850؛ كل قيم setpoint ومقارنة حدود قبوله، 48 قلبة bit منفردة بالـrecord، ومنع config/drive/save faults. ليس كل تسلسل حالات أو كل إعداد ولا برنامج24 |
| mutation: جعل ≥ threshold تصبح > | **كشف الخطأ: 9 failures** | `miss_threshold.log`؛ يثبت حساسية الاختبار عند مساواة الحد |
| mutation: تعطيل فحص valid أثناء evaluate | **كشف الخطأ: 8 failures** | `miss_invalid.log`؛ قناة غير صالحة في كل موضع |
| mutation: السماح بـACK عند reset+0.1°C | **كشف الخطأ: 8 failures** | `allow_hot_ack.log` و`allow_hot_ack-result.json`. محاولة أولى لتعطيل الشرط كليًا رفضها compiler بسبب unused parameter؛ عُدّل mutant إلى تغيير حد فعلي قابل للبناء |
| MSVC `/analyze` على protection/settings مع harness | **passed، بلا warnings** | `baseline-compile.log`. تحليل host لملفين فقط؛ لا تحليل كامل HAL/ISR ولا إثبات سلوك AVR. [مرجع Microsoft للأداة](https://learn.microsoft.com/en-us/cpp/build/reference/analyze-code-analysis?view=msvc-170) |
| محاولة تنسيق القناة10 بالـformatter القديم | **فجوة port أُعيد إنتاجها:** البداية `CH::` | `baseline.log`؛ ليست حالة مدعومة في 8ch، ولا تعني خطأ تشغيل القنوات1–8 |
| فشل ERC مع تقرير قديم clean | **failed: البوابة قبلت الفحص رغم exit=23** | `replay_erc_failure.py` و`erc-failure-result.json`؛ شرح أدناه |

**R-13 — نتيجة ERC قديمة يمكن أن تتحول إلى PASS جديد (مؤكد بإعادة إنتاج؛ تفصيل R-06).** استخرج الاختبار دالة `run_erc()` الأصلية من `gen/build.py` بواسطة AST وشغّلها منفردة، مع تقرير scratch قديم `** ERC messages: 0` وsubprocess يعيد فشلًا 23. النتيجة True. السبب أن الدالة تتجاهل returncode وتقرأ التقرير الموجود. لم أشغل build.py بالكامل؛ هذا اختبار للدالة مع فشل أداة محقون. الإصلاح المقترح: fail على خروج الأداة غير الصفري، وreport في مجلد run جديد، ورفض القديم/المفقود، وربط الدليل بالـhash. `check_netlist()` أيضًا يتجاهل returncode قبل قراءة XML؛ هذا خطر مماثل ظاهر من المصدر، ولم أختبره كحالة مستقلة. لا تثبت التجربة أن تقارير ERC الحالية قديمة؛ تقارير مراجعتي أنتجتها باستدعاء مستقل ناجح.

لإعادة الاختبار دون نموذج ذكاء اصطناعي: `python production/review-20261009-system/extended/run_extra.py` و`python production/review-20261009-system/extended/replay_erc_failure.py`. الأول يعتمد MSVC BuildTools بمسار الجهاز المسجل في script؛ لا يدّعي portability تلقائية. فشل mutants هنا متوقع ومطلوب، وليس فشل المصدر الأصلي. لا ينفذ أي من الأمرين كتابة hardware أو firmware الأصلية.

## 12. مصفوفة اختبار الجهاز: ما زال مطلوبًا قبل الاعتماد

الحالات: passed=أُجري ونجح، failed=أُجري وخالف المتوقع، blocked=تعذر تشغيله الآن، inconclusive=نُفذ ولم يكف الدليل. **الصفوف التالية blocked في هذه الجلسة** لغياب برنامج24 مؤهل ووحدة اختبار متصلة وأدوات القياس اللازمة؛ ليست اختبارات ناجحة ضمنيًا. معيار حرارة الخطأ والبيئة والنطاق النهائي يحتاج تثبيتًا قبل القياس؛ لا أخترع tolerances من عندي.

| الاختبار / المتطلب | الطريقة المقترحة | شرط النجاح والدليل المطلوب |
|---|---|---|
| كل قناة واسم موقعها R-1/R-8 | مصدر K/mV معاير مناسب، خطوة مستقلة لكل قناة، قبل/عند/بعد limit خاص بها | mapping صحيح، حدود مستقلة، خطأ ضمن ميزانية مكتوبة؛ سجل24 قناة |
| الاستجابة ≤1s R-2 | خطوة دخل عند phases مختلفة للـscan، خاصة بعد مرور دور القناة مباشرة؛ تزامن trigger المصدر مع قياس contact | أسوأ زمن فعلي لفتح contact ≤1s، شامل ADC/firmware/relay؛ waveform لا screenshot شاشة |
| open sensor R-6 | قطع T+ ثم T− وكلتيهما، وتكرار على كل موضع في rotation | تشخيص خلال مهلة معتمدة؛ اقتراح14slot الحالي لا يثبت نحو4s، ويلزم حل التعارض مع R-04 قبل PASS |
| reference/ground mixing R-1/R-7 | all insulated، all grounded، mixed، ثم فقد آخر grounded probe وقطع FEED/SENSE كلًا منفردًا | لا حرارة تبدو صالحة خارج نطاق common-mode؛ تسجيل حالة REF والـtrip/ alarm |
| CJ R-1 | ثبات مصدر thermocouple مع تغيير حرارة terminal والـLCD/relay/comms وحركة الهواء | حرارة معوضة ضمن budget؛ تقارب حساسي CJ وحده غير كافٍ |
| isolation/partial power R-3 | فصل island supply وحدها، ثم controller، وتشغيل power بالتتابع | no stale-valid/no unintended RUN، وعدم backfeed خارج حدود المصنّع؛ rails/pins/contact trace |
| hang/slow loop R-3 | fault injection: main hang مع timer شغال، interrupts off، SPI timeout، تشخيص لا يتقدم | إزالة السماح خلال المهلة المحددة، ولا يعيد WDT تغذية نفسه من مهمة منفصلة |
| ACK/startup R-5 | power cycles، قناة ساخنة/invalid/stale، ACK عالق ومكرر، فتح menu أثناء trip | لا RUN قبل اكتمال شروط البدء وACK صحيح، والعطل مرئي |
| EEPROM R-8 | قطع القدرة أثناء مراحل الحفظ، corruption، migration وقراءة back | آخر إعداد صالح أو config lock؛ لا اعتماد صامت لقيم افتراضية |
| Modbus R-9 | flood/CRC خاطئ/frames ناقصة/فصل كابل ومحاولات writes بلا local enable | الحماية مستمرة، لا remote RUN/ACK؛ توثيق bounds والـregister map |
| 50m cable / EMC R-7 | كابل وتركيب ممثلان للموقع، تشغيل أحمال اللوحة والـengine transients ضمن خطة مؤهلة | لا قراءة منخفضة صالحة زائفة؛ trace للسكة والـSPI والمدخل؛ لا حقن surge عشوائي على الماكينة |
| humidity/leakage I-105 | board مغسولة ومطلية ثم ظروف رطوبة/حرارة متفق عليها، قياس تسرب بطريقة مناسبة للـhigh impedance | حدود التسرب/الخطأ المكتوبة، لا مجرد continuity meter |
| تركيب وصيانة | فني لم يشارك في التصميم ينفذ ورقة الرسم ويستبدل unit/plug ويستعيد الإعدادات | لا أسئلة متكررة عن الطرف أو القناة أو إعادة التشغيل؛ سجل مواضع الالتباس |
| إنتاج الدفعة | fixture + serial + hashes + قراءات calibration + trip/contact test لكل لوحة | أثر قابل للتتبع لكل وحدة؛ اختبار نموذج واحد لا يثبت كل الدفعة |

لا تُنقل جميع الصفوف إلى برنامج أو منصة كبيرة فورًا. ابدأ fixture بسيطًا ودليلًا واحدًا، ثم جمّد الاختبارات المتكررة في scripts بلا LLM. الفني يرى test ID والنتيجة والإجراء؛ تفاصيل الأدوات تبقى في تقرير الاختبار.

## 13. أدوات إضافية: ما يفيد هنا فعلًا

| الأداة | القرار الآن | السبب/المصدر |
|---|---|---|
| MSVC `/analyze` + host C harness | استُخدمت بالفعل | موجودة على الجهاز؛ أضافت تحققًا دون dependency جديدة |
| Cppcheck | مرشح فحص ثانٍ لاحقًا، لم يُثبَّت أو يُشغّل هنا | يحتاج platform/config للـAVR حتى لا تصبح النتائج ضوضاء؛ [الدليل الرسمي](https://cppcheck.sourceforge.io/manual.html) |
| PulseView/sigrok مع logic analyzer مناسب | مرشح bring-up للـSPI وCS وPWM وtiming، وليس محاكاة للجهاز | [المشروع الرسمي](https://sigrok.org/wiki/Pulseview). اختيار العتاد ومستويات دخله والتحقق من acquisition لازم؛ scope مطلوب للـanalog ringing/rails |
| PyVISA/SCPI | عند وجود أجهزة bench تدعمه | أتمتة scope/supply/meter فقط بعد إثبات الاتصال والقياس؛ [التوثيق الرسمي](https://pyvisa.readthedocs.io/en/latest/introduction/getting.html). لا يخلق أداة قياس غير موجودة |
| simavr | تجربة محدودة لاحقًا للـtimers/WDT إذا دعم target الفعلي | يدعم AVR peripherals وVCD؛ [المستودع](https://github.com/buserror/simavr). لم أتحقق من اكتمال ATmega1284P لهذا المشروع، ولا نموذج AD7124 ممثل للدائرة |
| Wokwi | لا أعتمده محاكيًا مطابقًا للوحة الحالية | [القائمة الرسمية](https://docs.wokwi.com/getting-started/supported-hardware) تذكر AVR328P/2560/ATtiny85، لا target1284P المطلوب؛ demo على AVR مختلف لا يثبت هذه اللوحة |
| Renode / Labgrid / منصة HIL كبيرة | لا أضيفها الآن | قبل وجود target24 ووحدة وfixture، تكلفة الدمج لا تعالج فجوة القياس؛ لا حاجة إلى نقل architecture لتناسب أداة |

هذه قائمة اختيار مبنية على بحث رسمي وحالة الأدوات، وليست وعدًا بأن كلها مثبتة أو متوافقة. لم أستخدم أي أدوات تتحكم بالماكينة أو تحدث مخرجاتها.

## 14. الملفات والعمل بين agents: هل العدد أم النظام هو المشكلة؟

**القياس:** 263 ملفًا tracked إجمالًا؛ hardware/24ch فيه46، hardware/8ch فيه57، و33 ADR. وقت inventory كان `hardware/24ch/output` فيه146 ملفًا محليًا و`production` نحو1023، منها أدلة هذه المراجعة. الأعداد تتغير مع توليد الأدلة. المرجع `extended/structure-audit.json`. هذا ليس تضخمًا غير معقول في sources؛ معظم ضوضاء التصفح هي تجارب ومخرجات محلية، والمشكلة الأكبر تحديد المصدر المعتمد ومن يكتب عليه.

**R-17 — تعدد مصادر الحالة مع حماية كتابة غير شاملة (SRC مؤكد؛ توسيع R-06/R-10).** `finish.py` و`maze.py` و`fab.py` يستطيعون حفظ اللوحة مباشرة، ولا يظهر في مسارهم guard الـ24ch المطلوب. `board_provenance` القديم يخص8ch. و`.claude/settings.json` تعليمات خاصة بعميل واحد، لا قفل مشترَك بين Codex وClaude وKiCad. القول «كاتب واحد» في المستند لا يمنع process آخر من الكتابة. لم أُجر تجربة كتابتين متزامنتين على الأصل؛ لا حاجة للمخاطرة لإثبات غياب guard من المصدر.

الحل المقترح صغير داخل النظام الحالي، وليس إنشاء مجلد state جديد:

1. AGENTS وSTATE يعلنان المصدر النشط `hardware/24ch`، ووضع PCB الحالي incremental، وصاحب الكتابة ووقت بدء المهمة. لا تكون أسماء مثل finish23/finish24 في output مرجعًا ضمنيًا للنسخة المعتمدة.
2. guard واحد مشترك للأدوات الكاتبة: منع مع KiCad lock أو writer آخر، والتحقق من hash المتوقع قبل الحفظ. claim في STATE وحده تنسيق بشري، وليس lock ذريًا. لا تُغلق نافذة KiCad آليًا لتجاوز guard.
3. schematic مولّد من `gen/c_*.py` حسب README؛ PCB بعد تثبيت placement مصدره النسخة المحفوظة المعتمدة. لا يعيد agent تشغيل place/route كجزء من «validation». تعديل schematic يحتاج sync/parity ومراجعة ما تغير، لا افتراض أن كل الملفات تعاد من الصفر.
4. validation من snapshot بمجلد run فريد، وreport جديد/exit code صحيح، وhashes تربط firmware/BOM/CPL/PCB. عمل firmware ووثائق منفصلة ممكن بالتوازي؛ كاتبان على نفس الملف غير آمنين حتى لو مهمتاهما مختلفتان.
5. STATE ملخص قصير، ISSUES سجل البنود، ADR للقرارات. لا TODO/plan/handoff دائمًا لكل agent؛ التقرير الحالي منفصل بطلب المالك، وتُرحَّل فقط البنود المعتمدة لاحقًا بواسطة مهمة تنفيذ مصرح بها.
6. أحصر البحث الافتراضي في tracked sources، واستبعد production/output/archives من البحث العام. **لا تحذف الأدلة** بغرض جعل المجلد يبدو أنظف. أرشف حزمة الطلب الفعلية وربطها بالوحدة؛ قاعدة fabricated الحالية تخص8ch وتحتاج توسيع24ch عند التنفيذ.

**اختبار clone جديد مقترح، ولم يُنفذ هنا:** يبدأ عامل آخر من clone وبلا output محلي، فيحدد النسخة الحالية ويشغّل firmware وvalidate24 بلا ملف ناقص ولا تقرير موروث. ثم يحاكي فشل CLI ويثبت أن gate يفشل، ويثبت أن وجود writer lock يمنع الحفظ. البحث الحرفي وجد40 ذكرًا لمسارات مطلقة داخل مصادر/وثائق؛ الرقم ليس40 عيبًا، فبعضها أمثلة ومسارات أدوات قابلة للـoverride. النقطة التنفيذية هي توثيق prerequisites وأوامر المسارات الفعلية، لا إعادة تسمية ملفات المشروع جماعيًا.

**قائمة التسليم التي تقلل النقاش:** رسم توصيل site واحد، جدول24 قناة وحدودها ونوع probe، ورقة تشغيل/ACK، قائمة الأعطال والإجراء، سجل اختبار الوحدة، وحزمة إصدار واحدة برقم واضح. كل منها مطلوب لمستخدم مختلف؛ لا يُطلب من فني التشغيل قراءة33 قرارًا هندسيًا. يمكن جمعها في دليل جهاز واحد بدل خمسة مستندات متعارضة. كل ما سبق توصيات مراجعة، ولم أغيّر هيكل المشروع أو وثائقه.
