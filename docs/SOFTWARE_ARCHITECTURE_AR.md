# تقسيم البرنامج إلى MCAL / HAL / APP

## لماذا التقسيم؟

الهدف أن قرار المشروع لا يختلط بسجلات الميكرو أو بتفاصيل نوع الحساس. لو تغير
MAX6675 إلى MAX31856، تتغير طبقة Driver واحدة فقط، ويبقى منطق الشاشة والإنذار
كما هو. ولو تغير ATmega32 لاحقًا، نستبدل MCAL بدل إعادة كتابة التطبيق كله.

```text
APP: main + 100/95 C decision
             |
HAL: LCD | temperature sensor | alarm output
             |
MCAL: GPIO | SPI | board pin mapping
             |
Hardware: ATmega32A registers and pins
```

## MCAL — Microcontroller Abstraction Layer

هي الطبقة الوحيدة التي تعرف سجلات AVR وأرقام البورتات. لا تتخذ قرار تشغيل
الريلاي ولا تعرف معنى درجة الحرارة.

| الملف | الوظيفة |
|---|---|
| `include/mcal/gpio.h` | أنواع ودوال عامة لضبط اتجاه الرجل وكتابتها وقراءتها. |
| `src/mcal/gpio.c` | تنفيذ GPIO باستخدام DDRx وPORTx وPINx. |
| `include/mcal/spi.h` | واجهة بدء SPI ونقل بايت. |
| `src/mcal/spi.c` | إعداد SPI Hardware في ATmega32 وتنفيذ النقل. |
| `include/mcal/board.h` | أسماء أرجل اللوحة: LCD وCS وPB3. |
| `src/mcal/board.c` | ربط الأسماء بأرجل PORTA وPORTB الحقيقية. |

ميزة `board.c`: إذا نقلنا LED من PB3 إلى رجل أخرى، نغير Pin Mapping في مكان
واحد بدل البحث داخل جميع الملفات.

## HAL — Hardware Abstraction Layer

تحول الهاردوير إلى وظائف مفهومة للتطبيق. APP تطلب «اقرأ الحرارة» أو «شغل
الخرج»، ولا ترسل SPI أو تحرك بتات GPIO بنفسها.

| الملف | الوظيفة |
|---|---|
| `include/hal/lcd.h` | واجهة بدء الشاشة وطباعة سطر. |
| `src/hal/lcd.c` | HD44780 في 4-bit mode وإرسال البايت على مرحلتين. |
| `include/hal/temperature_sensor.h` | واجهة موحدة لعينة حرارة + Fault + نص حالة. |
| `src/hal/temperature_max6675.c` | Driver محاكاة Proteus: إطار 16-bit وOpen fault. |
| `src/hal/temperature_max31856.c` | Driver اللوحة: تهيئة K-Type وقراءة الحرارة والأعطال. |
| `include/hal/alarm_output.h` | واجهة تشغيل/فصل خرج الإنذار. |
| `src/hal/alarm_output.c` | يقود PB3 ويحفظ حالته الحالية. |

ملفا الحساس ينفذان نفس أسماء الدوال في `temperature_sensor.h`. أثناء البناء
يُربط **ملف واحد فقط** منهما مع بقية البرنامج، لذلك APP لا تحتاج `#ifdef` ولا
تعرف أي MAX مستخدم.

## APP — Application Layer

| الملف | الوظيفة |
|---|---|
| `include/app/app_config.h` | حدود التشغيل 1000 والفصل 950 بعُشر الدرجة. |
| `src/app/main.c` | تسلسل البرنامج، تنسيق LCD، Hysteresis، والتعامل مع Fault. |

APP تنفذ السياسة التالية:

```text
Fault?             -> Output OFF
Output OFF و T>=100 -> Output ON
Output ON  و T<=95  -> Output OFF
T بين 95 و100       -> احتفظ بالحالة السابقة
```

## كيف ينتج ملفا HEX؟

`firmware/build.ps1` يبني ملفات MCAL وHAL المشتركة وAPP مرة واحدة، ثم:

- يربطها مع `temperature_max31856.c` لينتج `thermocouple_meter_max31856.hex`.
- يربطها مع `temperature_max6675.c` لينتج `thermocouple_meter_max6675.hex`.

يستخدم البناء `-Wall -Wextra -Werror`؛ أي Warning يعامل كخطأ. كما يحذف فقط
ملفات البناء `.o/.elf/.hex` قبل البناء حتى لا يبقى HEX قديم لا يطابق السورس.

أمر البناء على هذا الجهاز:

```powershell
& D:\tasks\thermo\firmware\build.ps1
```

## ماذا نغير عند التوسعة؟

- حد الحرارة: `app_config.h` فقط.
- نوع حساس جديد: Driver جديد في HAL يطبق `temperature_sensor.h`.
- ريلاي إضافي: Output جديد في HAL، ثم سياسة جديدة في APP.
- ميكرو مختلف: MCAL وboard mapping، مع إبقاء واجهات HAL/APP قدر الإمكان.

## النتيجة الحالية

- MAX31856: البناء ناجح، Program 1954 bytes، Data 161 bytes.
- MAX6675: البناء ناجح، Program 1602 bytes، Data 109 bytes.
- لا توجد أخطاء أو تحذيرات Compile.
- اختبار PB3 داخل Proteus متروك للمستخدم بإضافة LED على الرجل الفعلية 4.
