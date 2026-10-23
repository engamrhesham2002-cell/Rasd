<div align="center">
  <img src="assets/rasd-logo.png" alt="Rasd logo" width="112" />
  <h1>Rasd | رَصْد</h1>
  <p><strong>Project file manager for engineering and technical-office work</strong></p>
  <p>مدير ملفات المشروعات الهندسية وأعمال المكتب الفني</p>
  <p>
    <a href="https://github.com/engamrhesham2002-cell/Rasd/releases"><strong>⬇ Download Rasd from Releases</strong></a>
    &nbsp;·&nbsp;
    <a href="#overview-ar">العربية</a>
    &nbsp;·&nbsp;
    <a href="#overview-en">English</a>
  </p>
  <p><a href="https://www.gnu.org/licenses/agpl-3.0.html"><img alt="License: AGPL-3.0" src="https://img.shields.io/badge/License-AGPL--3.0-blue.svg" /></a></p>
  <p><em>Made by ENG. Amr Hesham · صنعه م. عمرو هشام</em></p>
</div>

---

## Contents | الفهرس

- [نبذة عن Rasd](#overview-ar)
- [مميزات البرنامج](#features-ar)
- [التنزيل والتشغيل](#download-ar)
- [صور من البرنامج](#screenshots-ar)
- [ملاحظات وحدود المعاينة](#notes-ar)
- [الترخيص](#license-ar)
- [ما القادم؟](#roadmap-ar)
- [كلمة من المطور](#about-author-ar)
- [About Rasd](#overview-en)
- [Features](#features-en)
- [Download and run](#download-en)
- [Screenshots](#screenshots-en)
- [Preview notes and limitations](#notes-en)
- [What’s next?](#roadmap-en)
- [About the developer](#about-author-en)

<a id="overview-ar"></a>
## نبذة عن Rasd

**Rasd (رَصْد)** برنامج ويندوز يساعد على تنظيم ملفات المشروعات الهندسية والمكتبية والبحث فيها ومعاينة أنواع متعددة منها من واجهة واحدة. صممته عشان يسهل عليّ وعلى زملائي الوصول لملفات المشروع اليومية.

> **التنزيل:** [افتح صفحة الإصدارات Releases](https://github.com/engamrhesham2002-cell/Rasd/releases) واختر النسخة المناسبة. رابط الإصدارات سيظل ثابتًا مع التحديثات.

<a id="features-ar"></a>
## مميزات البرنامج

- إنشاء المشروعات وتصفح مجلداتها وملفاتها من واجهة واحدة.
- بحث داخل المشروع المفتوح باستخدام محرك **Everything** المضمّن، مع بحث محلي احتياطي عند تعذر تشغيل المحرك.
- تصفية الملفات حسب النوع والامتداد، وعرض معلومات الملف وموقعه وحجمه.
- معاينة الصور وPDF وملفات Excel وDOCX والملفات النصية، ومعاينة DXF. معاينة DWG تعتمد على توفر معاينة مناسبة أو أدوات AutoCAD على الجهاز.
- إضافة هاشتاجات للملفات وتخصصات للمجلدات، وحفظ المفضلة.
- الوصول إلى الملفات التي فُتحت مؤخرًا والملفات التي أضيفت حديثًا وسجل نشاط البرنامج.
- تثبيت اختياري لكلمة مرور لفتح البرنامج. كلمة المرور لا تشفر ملفات المشروع.
- التحقق من وجود تحديث منشور على GitHub عند بدء التشغيل، مع خيار تنزيله فورًا أو تجهيزه للتثبيت في المرة القادمة أو تأجيل التنبيه ليوم.

<a id="download-ar"></a>
## التنزيل والتشغيل

نزّل ملف التثبيت من [صفحة Releases](https://github.com/engamrhesham2002-cell/Rasd/releases). النسختان القياسية والمحمولة تضمان Python ومكتبات البرنامج ومحرك Everything، لذلك لا تحتاج لتثبيت Python أو تنزيل مكونات وقت التشغيل من الإنترنت.

- **Standard installer:** يتيح اختيار مجلد التثبيت، وينشئ مجلد `Log` بجوار البرنامج.
- **Portable installer:** ينشئ مجلدًا محمولًا بجوار ملف التثبيت؛ انقل المجلد كاملًا بعد إغلاق البرنامج، مع إبقاء `Rasd.exe` و`Log` معًا.
- أنشئ كل مشروع داخل مجلد مستقل ضمن `Log` بجوار البرنامج. يقتصر البحث على المشروع المفتوح.

### للمطورين

يتوفر الكود المصدري المقسّم ونسخة كاملة مدمجة في [`source/v0.39`](source/v0.39). تعليمات البناء ومتطلباته موجودة في مجلد النسخة. المشروع مبني بـPython 3.11 وTkinter؛ راجع ملفات المصدر والتراخيص المرفقة قبل إعادة التوزيع.

> **ملاحظة التحديث:** يتضمن Rasd v0.39 فحص الإصدارات وتطبيق التحديثات. الانتقال الأول من v0.38 إلى v0.39 يحتاج تشغيل مثبت v0.39 يدويًا؛ الإصدارات التالية يمكن تحديثها من داخل البرنامج.

<a id="screenshots-ar"></a>
## صور من البرنامج

<div align="center">
  <img src="assets/screenshots/welcome.png" alt="شاشة البداية" width="48%" />
  <img src="assets/screenshots/projects-dashboard.png" alt="واجهة المشروعات" width="48%" />
</div>
<div align="center">
  <img src="assets/screenshots/project-browser.png" alt="تصفح ملفات المشروع" width="48%" />
  <img src="assets/screenshots/search-results.png" alt="نتائج البحث داخل المشروع" width="48%" />
</div>
<div align="center">
  <img src="assets/screenshots/file-preview-pdf.png" alt="معاينة PDF" width="32%" />
  <img src="assets/screenshots/file-preview-image.png" alt="معاينة صورة" width="32%" />
  <img src="assets/screenshots/file-preview-cad.png" alt="مثال معاينة CAD" width="32%" />
</div>
<div align="center">
  <img src="assets/screenshots/file-tags.png" alt="إدارة هاشتاجات الملفات" width="48%" />
  <img src="assets/screenshots/folder-specialties.png" alt="تخصيص المجلدات" width="48%" />
</div>

<a id="notes-ar"></a>
## ملاحظات وحدود المعاينة

- معاينة PDF وExcel داخل البرنامج مخصصة للعرض؛ لا تعدّل ملفات المصدر ولا تعيد حساب معادلات Excel.
- معاينة DWG ليست مضمونة على كل جهاز؛ تعتمد على وجود ملف PDF أو صورة مرتبطة، أو صورة مصغرة من Windows، أو AutoCAD Core Console متاح.
- معاينة Excel تعرض البيانات على صفحات، وقد لا تظهر نتائج المعادلات إذا لم تكن محفوظة داخل الملف.
- فتح الملفات خارجيًا يعتمد على البرامج المثبتة وارتباطات الملفات في Windows.
- ملفات المشروع تبقى ملفات عادية داخل `Log`، وقفل البرنامج الاختياري لا يشفرها.

<a id="license-ar"></a>
## الترخيص

كود Rasd منشور بموجب **AGPL-3.0**؛ راجع ملف [`LICENSE`](LICENSE). راجع [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) لتراخيص المكونات المضمّنة، ومنها Everything وPyMuPDF.
<a id="roadmap-ar"></a>
## ما القادم؟

دي خريطة تطوير Rasd الحالية. علامة **تمام** معناها إن الميزة موجودة في الإصدار الموضح؛ والشرطة معناها إنها لسه ضمن الأفكار القادمة.

| # | الميزة | الحالة | الإصدار |
|---|---|---|---|
| 1 | معاينة الفيديوهات بصيغ مختلفة | — | — |
| 2 | تكبير وتصغير وتحريك واجهة المعاينة بسلاسة | — | — |
| 3 | ربط ملفات المشروع ببعض، وإظهار الملفات المرتبطة من قائمة الزر الأيمن مع حفظ الروابط داخل Rasd | — | — |
| 4 | قائمة مهام To-do داخل البرنامج | — | — |
| 5 | تقويم للمهام والمواعيد والفعاليات | — | — |
| 6 | حفظ اختصارات لمواقع مهمة للشغل | — | — |
| 7 | اختصارات لبرامج الشغل | — | — |
| 8 | تحسين الواجهة وتجربة الاستخدام باستمرار | — | — |
| 9 | التحقق من تحديثات GitHub والتنزيل والتثبيت من داخل Rasd، مع تأجيل التنبيه أو تجهيز التحديث للتشغيل القادم | تمام | v0.39 |
| 10 | إدارة وتنظيم مجلد `Log` من داخل البرنامج، مع تصدير مشروع كامل أو ملفات ومجلدات مختارة | — | — |
| 11 | شاشة تعريف تفاعلية تظهر عند أول تشغيل بعد التثبيت | — | — |
| Bonus | إضافة أوامر CAD كأدوات اختيارية داخل Rasd | — | — |

### التحديث ببساطة

يفحص Rasd صفحة الإصدارات على GitHub عند بدء التشغيل. لو فيه إصدار أحدث، تقدر تأجل التنبيه ليوم، أو تنزّل التحديث وتثبته فورًا، أو تخليه جاهزًا ليتثبت عند تشغيل البرنامج المرة القادمة. Rasd يتحقق من سلامة ملف التثبيت قبل تشغيله، ويغلق نفسه وقت التثبيت ثم يفتح من جديد. ملفات المشاريع داخل `Log` تظل محفوظة. الاتصال بالإنترنت مطلوب للفحص والتنزيل فقط. لا يحتاج المستخدم ملف BAT أو أوامر يدوية؛ التحديث مدمج في البرنامج.<a id="about-author-ar"></a>
## كلمة من المطور

أنا عمرو هشام محمود، مهندس مكتب فني في مجال الري والصرف الزراعي واللاندسكيب. أنا مش مبرمج؛ استخدمت أدوات الذكاء الاصطناعي في إنشاء Rasd، وكان دوري طرح الأفكار وتوجيه الأدوات للوصول لبرنامج يساعدني في شغلي. كنت أتمنى أدرس حاسبات ومعلومات، لكن الظروف ما سمحتش وقتها. بإذن الله هسعى أتعلم البرمجة لما ألاقي الوقت المناسب، وهكمل تطوير أدوات تساعدني وتساعد زملائي.

ما بنسبش لنفسي فضل كتابة الكود؛ الذكاء الاصطناعي تولّى كتابة الكود وتنفيذ البرنامج بالكامل. أنا كنت صاحب الأفكار، ووجّهت أدوات الذكاء الاصطناعي خطوة بخطوة لحد ما نفّذت الفكرة اللي كانت في دماغي. وبشكر مطوري **Everything** على محرك البحث الممتاز اللي ألهمني وأستخدمه داخل Rasd للبحث في ملفات المشروع. هدفي إني أطور البرنامج مع الوقت وأشاركه مع الآخرين.

<a id="overview-en"></a>
## About Rasd

**Rasd (رَصْد)** is a Windows application for organizing, searching, and previewing engineering and technical-office project files from one place. I built it to make everyday project files easier for me and my colleagues to find.

> **Download:** Visit the [GitHub Releases page](https://github.com/engamrhesham2002-cell/Rasd/releases) and choose the installer that fits your needs. This link remains stable across updates.

<a id="features-en"></a>
## Features

- Create projects and browse their folders and files in one interface.
- Search within the open project using the bundled **Everything** engine, with a local fallback if the engine cannot run.
- Filter files by type and extension, and view file details and project paths.
- Preview images, PDFs, Excel workbooks, DOCX, and text files, plus DXF drawings. DWG preview depends on suitable previews or AutoCAD tools being available on the computer.
- Add file hashtags and folder specialties, and save favorites.
- Revisit recently opened files, recently added files, and activity recorded by the application.
- Check GitHub Releases for updates at startup, then download now, prepare an update for the next launch, or snooze the reminder for one day.
- Optional password prompt when opening the app. It does not encrypt project files.

<a id="download-en"></a>
## Download and run

Download an installer from the [Releases page](https://github.com/engamrhesham2002-cell/Rasd/releases). Both the standard and portable installers bundle Python, the application libraries, and Everything, so users do not need to install Python or download runtime components.

- **Standard installer:** lets you choose an installation folder and creates a `Log` folder beside the app.
- **Portable installer:** creates a portable folder beside the installer. Close Rasd before moving that complete folder, and keep `Rasd.exe` and `Log` together.
- Create each project in its own subfolder inside `Log`, which is beside the application. Search is scoped to the open project.

### For developers

The split source modules and the merged single-file source are in [`source/v0.39`](source/v0.39). Build instructions and requirements are included there. Rasd uses Python 3.11 and Tkinter; review the source and accompanying third-party licenses before redistribution.

> **Update note:** Rasd v0.39 adds release checks and in-app updates. The first move from v0.38 to v0.39 requires manually running the v0.39 installer; later versions can update from within the app.

<a id="screenshots-en"></a>
## Screenshots

The screenshots above show the welcome screen, project dashboard, file browser, project search, and representative previews and organization tools.

<a id="notes-en"></a>
## Preview notes and limitations

- PDF and Excel previews are for viewing; they do not edit the original file or recalculate Excel formulas.
- DWG preview is not guaranteed on every computer. It depends on a related PDF/image, a Windows thumbnail, or an available AutoCAD Core Console.
- Excel data is shown in pages; formula results may be absent when they are not saved in the workbook.
- Opening files externally depends on applications installed and Windows file associations.
- Project files remain ordinary files in `Log`; the optional application password does not encrypt them.

<a id="license-en"></a>
## License

Rasd is licensed under **AGPL-3.0**; see [`LICENSE`](LICENSE). See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for bundled component notices, including Everything and PyMuPDF.
<a id="roadmap-en"></a>
## What’s coming?

This is Rasd’s current development roadmap. **Done** means the feature is included in the listed version; a dash means it remains planned.

| # | Feature | Status | Version |
|---|---|---|---|
| 1 | Preview videos in multiple formats | — | — |
| 2 | Smooth zooming and panning in the preview pane | — | — |
| 3 | Link project files, open linked items from the right-click menu, and save those links in Rasd | — | — |
| 4 | An in-app to-do list | — | — |
| 5 | A calendar for tasks, appointments, and events | — | — |
| 6 | Saved shortcuts to important work websites | — | — |
| 7 | Shortcuts for work applications | — | — |
| 8 | Ongoing interface and usability improvements | — | — |
| 9 | Check GitHub for updates, download and install from Rasd, snooze the notice, or prepare an update for the next launch | Done | v0.39 |
| 10 | Manage and organize the `Log` folder in Rasd, including exporting a whole project or selected files and folders | — | — |
| 11 | An interactive first-run tutorial after installation | — | — |
| Bonus | Add optional CAD commands as tools inside Rasd | — | — |

### Updates in plain language

Rasd checks its GitHub Releases page when it starts. If a newer version is available, you can snooze the reminder for a day, download and install now, or download now and install the next time Rasd starts. Rasd verifies the installer before running it, closes during installation, and then opens again. Project files in `Log` are preserved. Internet access is needed only to check for and download updates. Users do not need a BAT file or manual commands; updating is built into Rasd.<a id="about-author-en"></a>
## About the developer

I’m Amr Hesham Mahmoud, a technical-office engineer working in agricultural irrigation, drainage, and landscaping. I’m not a programmer; I used AI tools to build Rasd. My part was to bring the ideas and guide those tools toward something useful for my work. I had hoped to study computer science, but circumstances did not allow it at the time. I hope to learn programming in the future and keep building tools that help me and my colleagues.

I don’t claim credit for writing the code; AI handled the coding and implementation of the application. I brought the ideas and guided the AI step by step to build what I had in mind. I’m grateful to the developers of **Everything** for their excellent search engine, which inspired me and is used by Rasd to search within a project. I hope to keep improving the application and sharing it with others.

---

**Rasd · Made by ENG. Amr Hesham**
