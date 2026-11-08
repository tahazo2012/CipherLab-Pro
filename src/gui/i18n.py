"""Lightweight UI translation: English, Persian (fa), Arabic (ar), Chinese (zh) and Russian (ru).

Design: the code keeps writing English strings. ``retranslate`` walks the widget tree, remembers each
widget's original English text in Qt dynamic properties, and swaps in the translation. Switching back to
English restores the originals. Texts without an entry stay English (technical names, dialogs, error
messages from the core, the analysis report and the About page are intentionally not translated).
"""
from __future__ import annotations

from typing import Callable, Iterator

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QLabel, QLineEdit, QMainWindow,
                               QPlainTextEdit, QSpinBox, QTabWidget, QTableWidget, QWidget)

LANGS: dict[str, str] = {"en": "English", "fa": "فارسی", "ar": "العربية", "zh": "中文", "ru": "Русский"}
RTL_LANGS = {"fa", "ar"}

# (English, Persian, Arabic, Chinese)
_ROWS: list[tuple[str, str, str, str]] = [
    # ---- tabs
    ("Encode", "کدگذاری", "ترميز", "编码"),
    ("Decode", "کدگشایی", "فك الترميز", "解码"),
    ("Encrypt", "رمزنگاری", "تشفير", "加密"),
    ("Decrypt", "رمزگشایی", "فك التشفير", "解密"),
    ("Hex Analyzer", "تحلیلگر هگز", "محلل Hex", "十六进制分析器"),
    ("XOR Analyzer", "تحلیلگر XOR", "محلل XOR", "XOR 分析器"),
    ("Compare Results", "مقایسه نتایج", "مقارنة النتائج", "结果对比"),
    ("History", "تاریخچه", "السجل", "历史记录"),
    ("About", "درباره", "حول", "关于"),
    ("Settings", "تنظیمات", "الإعدادات", "设置"),
    # ---- common buttons / tooltips
    ("Paste", "چسباندن", "لصق", "粘贴"),
    ("Copy", "کپی", "نسخ", "复制"),
    ("Clear", "پاک کردن", "مسح", "清除"),
    ("Import…", "وارد کردن…", "استيراد…", "导入…"),
    ("Export…", "خروجی گرفتن…", "تصدير…", "导出…"),
    ("Analyze", "تحلیل", "تحليل", "分析"),
    ("Cancel", "لغو", "إلغاء", "取消"),
    ("Run", "اجرا", "تشغيل", "运行"),
    ("Show", "نمایش", "إظهار", "显示"),
    ("Replace the content with the clipboard text", "جایگزینی محتوا با متن کلیپ‌بورد", "استبدال المحتوى بنص الحافظة", "用剪贴板文本替换内容"),
    ("Copy to the clipboard", "کپی در کلیپ‌بورد", "نسخ إلى الحافظة", "复制到剪贴板"),
    ("Clear this editor", "پاک کردن این ویرایشگر", "مسح هذا المحرر", "清空此编辑器"),
    ("Load a TXT / HEX / JSON / binary file (or drop one here)", "بارگذاری فایل TXT / HEX / JSON / باینری (یا رها کردن فایل اینجا)", "تحميل ملف TXT / HEX / JSON / ثنائي (أو أسقط ملفًا هنا)", "加载 TXT / HEX / JSON / 二进制文件(或拖放到此处)"),
    ("Save the content to a file", "ذخیره‌ی محتوا در فایل", "حفظ المحتوى في ملف", "将内容保存到文件"),
    # ---- pane titles
    ("Text to encode", "متن برای کدگذاری", "النص المراد ترميزه", "待编码文本"),
    ("Encoded result", "نتیجه‌ی کدگذاری", "نتيجة الترميز", "编码结果"),
    ("Encoded input", "ورودی کدگذاری‌شده", "المدخل المرمَّز", "已编码输入"),
    ("Decoded result", "نتیجه‌ی کدگشایی", "نتيجة فك الترميز", "解码结果"),
    ("Plaintext / message", "متن ساده / پیام", "النص الأصلي / الرسالة", "明文 / 消息"),
    ("Result", "نتیجه", "النتيجة", "结果"),
    ("Encrypted data", "داده‌ی رمزنگاری‌شده", "البيانات المشفّرة", "加密数据"),
    ("Decrypted result", "نتیجه‌ی رمزگشایی", "نتيجة فك التشفير", "解密结果"),
    ("Hexadecimal input", "ورودی هگزادسیمال", "مدخل سداسي عشري", "十六进制输入"),
    ("Input bytes", "بایت‌های ورودی", "بايتات الإدخال", "输入字节"),
    # ---- placeholders
    ("Type or paste text (Persian, Arabic, English, emoji…)", "متن را تایپ یا جای‌گذاری کنید (فارسی، عربی، انگلیسی، ایموجی…)", "اكتب النص أو الصقه (فارسي، عربي، إنجليزي، رموز تعبيرية…)", "输入或粘贴文本(波斯语、阿拉伯语、英语、表情符号…)"),
    ("Message to encrypt or hash", "پیام برای رمزنگاری یا هش", "الرسالة المراد تشفيرها أو حساب بصمتها", "要加密或哈希的消息"),
    ("Password (never saved or logged)", "رمز عبور (هرگز ذخیره یا ثبت نمی‌شود)", "كلمة المرور (لا تُحفظ ولا تُسجَّل أبدًا)", "密码(绝不保存或记录)"),
    ("Key (never saved or logged)", "کلید (هرگز ذخیره یا ثبت نمی‌شود)", "المفتاح (لا يُحفظ ولا يُسجَّل أبدًا)", "密钥(绝不保存或记录)"),
    ("Paste the CipherLab Pro JSON container (or XOR hex)", "کانتینر JSON برنامه‌ی CipherLab Pro (یا هگز XOR) را جای‌گذاری کنید", "الصق حاوية JSON الخاصة بـ CipherLab Pro (أو XOR بصيغة Hex)", "粘贴 CipherLab Pro 的 JSON 容器(或 XOR 十六进制)"),
    ("Raw key (AES key-mode / XOR; never saved or logged)", "کلید خام (حالت کلید AES / XOR؛ هرگز ذخیره یا ثبت نمی‌شود)", "مفتاح خام (وضع مفتاح AES / XOR؛ لا يُحفظ ولا يُسجَّل أبدًا)", "原始密钥(AES 密钥模式 / XOR;绝不保存或记录)"),
    ("Ciphertext as hex (or switch to UTF-8 text)", "متن رمزشده به صورت هگز (یا تغییر به متن UTF-8)", "النص المشفّر بصيغة Hex (أو بدّل إلى نص UTF-8)", "十六进制密文(或切换为 UTF-8 文本)"),
    ("Known key (never saved)", "کلید معلوم (ذخیره نمی‌شود)", "مفتاح معروف (لا يُحفظ)", "已知密钥(不保存)"),
    ("Search history…", "جست‌وجو در تاریخچه…", "البحث في السجل…", "搜索历史记录…"),
    ("The analysis report appears here.", "گزارش تحلیل اینجا نمایش داده می‌شود.", "يظهر تقرير التحليل هنا.", "分析报告将显示在此处。"),
    ("Key-length ranking appears here.", "رتبه‌بندی طول کلید اینجا نمایش داده می‌شود.", "يظهر ترتيب أطوال المفاتيح هنا.", "密钥长度排名将显示在此处。"),
    ("Select a candidate to see how it was scored.", "یک گزینه را انتخاب کنید تا نحوه‌ی امتیازدهی آن را ببینید.", "اختر مرشحًا لرؤية كيفية تقييمه.", "选择一个候选项以查看其评分方式。"),
    # ---- encode / decode
    ("Text encoding:", "کدگذاری متن:", "ترميز النص:", "文本编码:"),
    ("Output format:", "قالب خروجی:", "تنسيق الإخراج:", "输出格式:"),
    ("Hex separator: space", "جداکننده‌ی هگز: فاصله", "فاصل Hex: مسافة", "十六进制分隔符:空格"),
    ("Hex separator: none", "جداکننده‌ی هگز: بدون", "فاصل Hex: بدون", "十六进制分隔符:无"),
    ("Uppercase hex", "هگز با حروف بزرگ", "Hex بأحرف كبيرة", "大写十六进制"),
    ("Hexadecimal", "هگزادسیمال", "سداسي عشري", "十六进制"),
    ("URL (percent) encoding", "کدگذاری URL (درصدی)", "ترميز URL (النسبة المئوية)", "URL(百分号)编码"),
    ("Unicode escape (\\uXXXX)", "دنباله‌ی گریز یونیکد (\\uXXXX)", "تسلسل هروب Unicode (\\uXXXX)", "Unicode 转义 (\\uXXXX)"),
    ("JSON string escape", "گریز رشته‌ی JSON", "هروب سلسلة JSON", "JSON 字符串转义"),
    ("Binary (8-bit groups)", "دودویی (گروه‌های ۸ بیتی)", "ثنائي (مجموعات 8 بت)", "二进制(8 位一组)"),
    ("Decimal bytes", "بایت‌های دهدهی", "بايتات عشرية", "十进制字节"),
    ("Input format:", "قالب ورودی:", "تنسيق الإدخال:", "输入格式:"),
    ("Interpret bytes as:", "تفسیر بایت‌ها به صورت:", "تفسير البايتات على أنها:", "将字节解释为:"),
    ("Strict: report invalid bytes", "سخت‌گیرانه: گزارش بایت‌های نامعتبر", "صارم: الإبلاغ عن البايتات غير الصالحة", "严格:报告无效字节"),
    ("Replace invalid bytes with U+FFFD (lossy)", "جایگزینی بایت‌های نامعتبر با U+FFFD (با اتلاف)", "استبدال البايتات غير الصالحة بـ U+FFFD (مع فقدان)", "用 U+FFFD 替换无效字节(有损)"),
    ("Suggest format", "پیشنهاد قالب", "اقتراح التنسيق", "建议格式"),
    ("List the formats the input could be written in (ambiguity is reported, not hidden)", "فهرست قالب‌هایی که ورودی می‌تواند در آن‌ها نوشته شده باشد (ابهام گزارش می‌شود، پنهان نمی‌شود)", "عرض التنسيقات التي قد يكون المدخل مكتوبًا بها (يُبلَّغ عن الغموض ولا يُخفى)", "列出输入可能使用的格式(会报告歧义,不会隐藏)"),
    ("Raw bytes as hexadecimal (no text decoding)", "بایت‌های خام به صورت هگزادسیمال (بدون کدگشایی متن)", "البايتات الخام بصيغة سداسية عشرية (دون فك ترميز النص)", "原始字节(十六进制,不做文本解码)"),
    # ---- encrypt / decrypt
    ("Algorithm:", "الگوریتم:", "الخوارزمية:", "算法:"),
    ("AES-256-GCM (password)", "AES-256-GCM (با رمز عبور)", "AES-256-GCM (بكلمة مرور)", "AES-256-GCM(密码)"),
    ("AES-GCM (raw key, hex)", "AES-GCM (کلید خام، هگز)", "AES-GCM (مفتاح خام، Hex)", "AES-GCM(原始密钥,十六进制)"),
    ("Repeating-key XOR (educational, NOT secure)", "XOR با کلید تکرارشونده (آموزشی، ناامن)", "XOR بمفتاح متكرر (تعليمي، غير آمن)", "重复密钥 XOR(仅供学习,不安全)"),
    ("SHA-256 hash (not encryption)", "هش SHA-256 (رمزنگاری نیست)", "بصمة SHA-256 (ليست تشفيرًا)", "SHA-256 哈希(不是加密)"),
    ("SHA-512 hash (not encryption)", "هش SHA-512 (رمزنگاری نیست)", "بصمة SHA-512 (ليست تشفيرًا)", "SHA-512 哈希(不是加密)"),
    ("HMAC-SHA256 (authentication, not encryption)", "HMAC-SHA256 (احراز اصالت، رمزنگاری نیست)", "HMAC-SHA256 (مصادقة، وليست تشفيرًا)", "HMAC-SHA256(认证,不是加密)"),
    ("HMAC-SHA512 (authentication, not encryption)", "HMAC-SHA512 (احراز اصالت، رمزنگاری نیست)", "HMAC-SHA512 (مصادقة، وليست تشفيرًا)", "HMAC-SHA512(认证,不是加密)"),
    ("Input is UTF-8 text", "ورودی متن UTF-8 است", "المدخل نص UTF-8", "输入为 UTF-8 文本"),
    ("Input is hexadecimal bytes", "ورودی بایت‌های هگزادسیمال است", "المدخل بايتات بصيغة سداسية عشرية", "输入为十六进制字节"),
    ("Key as text", "کلید به صورت متن", "المفتاح كنص", "密钥为文本"),
    ("Key as hex", "کلید به صورت هگز", "المفتاح بصيغة Hex", "密钥为十六进制"),
    ("XOR with a repeating key is trivially breakable. Use it only to learn how XOR works.", "XOR با کلید تکرارشونده به‌سادگی شکسته می‌شود. فقط برای یادگیری طرز کار XOR از آن استفاده کنید.", "يمكن كسر XOR بمفتاح متكرر بسهولة. استخدمه فقط لتعلّم كيفية عمل XOR.", "重复密钥 XOR 很容易被破解,仅用于学习 XOR 的原理。"),
    ("A hash is one-way and cannot be decrypted. It is neither encryption nor encoding.", "هش یک‌طرفه است و قابل رمزگشایی نیست. نه رمزنگاری است و نه کدگذاری.", "البصمة (Hash) أحادية الاتجاه ولا يمكن فك تشفيرها. وهي ليست تشفيرًا ولا ترميزًا.", "哈希是单向的,无法解密。它既不是加密,也不是编码。"),
    ("HMAC proves integrity/authenticity with a secret key; it does not hide the message.", "HMAC با یک کلید محرمانه، صحت و اصالت پیام را ثابت می‌کند؛ پیام را پنهان نمی‌کند.", "يثبت HMAC سلامة الرسالة وأصالتها بمفتاح سري؛ لكنه لا يخفي الرسالة.", "HMAC 使用密钥证明消息的完整性和真实性,但不会隐藏消息内容。"),
    ("AES-GCM container (JSON from the Encrypt tab)", "کانتینر AES-GCM (JSON تب رمزنگاری)", "حاوية AES-GCM (JSON من تبويب التشفير)", "AES-GCM 容器(来自“加密”标签页的 JSON)"),
    ("Repeating-key XOR (input as hex)", "XOR با کلید تکرارشونده (ورودی هگز)", "XOR بمفتاح متكرر (المدخل بصيغة Hex)", "重复密钥 XOR(输入为十六进制)"),
    # ---- analyzers
    ("Include bounded repeating-key XOR analysis", "شامل تحلیل XOR کلید تکرارشونده (محدود)", "تضمين تحليل XOR بمفتاح متكرر (محدود)", "包含有限的重复密钥 XOR 分析"),
    ("Input is hexadecimal", "ورودی هگزادسیمال است", "المدخل سداسي عشري", "输入为十六进制"),
    ("Single-byte XOR analysis", "تحلیل XOR تک‌بایتی", "تحليل XOR بايت واحد", "单字节 XOR 分析"),
    ("Repeating-key XOR analysis (bounded)", "تحلیل XOR کلید تکرارشونده (محدود)", "تحليل XOR بمفتاح متكرر (محدود)", "重复密钥 XOR 分析(有限制)"),
    ("max key length", "حداکثر طول کلید", "أقصى طول للمفتاح", "最大密钥长度"),
    ("top", "برترین", "أفضل", "前"),
    ("Apply key", "اعمال کلید", "تطبيق المفتاح", "应用密钥"),
    ("XOR is not secure encryption. Results are statistical guesses; readable output is evidence, not proof.", "XOR رمزنگاری امن نیست. نتایج حدس‌های آماری‌اند؛ خروجی خوانا شاهد است، نه اثبات.", "XOR ليس تشفيرًا آمنًا. النتائج تخمينات إحصائية؛ والمخرجات المقروءة دليل وليست إثباتًا.", "XOR 不是安全的加密。结果只是统计推测;可读的输出是证据,而不是证明。"),
    ("Method", "روش", "الطريقة", "方法"),
    ("Score", "امتیاز", "الدرجة", "得分"),
    ("Confidence", "اطمینان", "الثقة", "置信度"),
    ("Printable", "قابل چاپ", "قابل للطباعة", "可打印"),
    ("Errors", "خطاها", "الأخطاء", "错误"),
    ("Copy output (text)", "کپی خروجی (متن)", "نسخ المخرجات (نص)", "复制输出(文本)"),
    ("Copy output (hex)", "کپی خروجی (هگز)", "نسخ المخرجات (Hex)", "复制输出(十六进制)"),
    ("Send selected to Compare", "ارسال موارد انتخابی به مقایسه", "إرسال المحدد إلى المقارنة", "将所选项发送到对比"),
    ("Send all to Compare", "ارسال همه به مقایسه", "إرسال الكل إلى المقارنة", "将全部发送到对比"),
    ("Copy the decoded text of the selected candidate", "کپی متن کدگشایی‌شده‌ی گزینه‌ی انتخابی", "نسخ النص المفكوك للمرشح المحدد", "复制所选候选项的解码文本"),
    ("Copy the full output bytes as hexadecimal", "کپی همه‌ی بایت‌های خروجی به صورت هگز", "نسخ كل بايتات المخرجات بصيغة Hex", "以十六进制复制全部输出字节"),
    ("Add the selected candidates to the Compare Results tab", "افزودن گزینه‌های انتخابی به تب مقایسه‌ی نتایج", "إضافة المرشحين المحددين إلى تبويب مقارنة النتائج", "将所选候选项添加到“结果对比”标签页"),
    ("Add every candidate to the Compare Results tab", "افزودن همه‌ی گزینه‌ها به تب مقایسه‌ی نتایج", "إضافة كل المرشحين إلى تبويب مقارنة النتائج", "将所有候选项添加到“结果对比”标签页"),
    # ---- compare
    ("Send candidates here from the Hex Analyzer or XOR Analyzer tabs to compare them side by side.", "گزینه‌ها را از تب‌های تحلیلگر هگز یا تحلیلگر XOR به اینجا بفرستید تا کنار هم مقایسه شوند.", "أرسل المرشحين من تبويبي محلل Hex أو محلل XOR إلى هنا لمقارنتهم جنبًا إلى جنب.", "从“十六进制分析器”或“XOR 分析器”标签页发送候选项到这里,即可并排对比。"),
    ("Remove selected column", "حذف ستون انتخابی", "إزالة العمود المحدد", "删除所选列"),
    ("Export JSON…", "خروجی JSON…", "تصدير JSON…", "导出 JSON…"),
    ("Quality × prior", "کیفیت × پیش‌احتمال", "الجودة × الاحتمال المسبق", "质量 × 先验"),
    ("Printable ratio", "نسبت قابل چاپ", "نسبة القابل للطباعة", "可打印比例"),
    ("Decoding errors", "خطاهای کدگشایی", "أخطاء فك الترميز", "解码错误"),
    ("Entropy (bits/byte)", "آنتروپی (بیت/بایت)", "الإنتروبيا (بت/بايت)", "熵(比特/字节)"),
    ("Key (hex)", "کلید (هگز)", "المفتاح (Hex)", "密钥(十六进制)"),
    ("Output preview", "پیش‌نمایش خروجی", "معاينة المخرجات", "输出预览"),
    ("Why", "دلیل", "السبب", "原因"),
    # ---- history
    ("Record history", "ثبت تاریخچه", "تسجيل السجل", "记录历史"),
    ("Time (UTC)", "زمان (UTC)", "الوقت (UTC)", "时间 (UTC)"),
    ("Operation", "عملیات", "العملية", "操作"),
    ("Summary", "خلاصه", "الملخص", "摘要"),
    ("Input preview", "پیش‌نمایش ورودی", "معاينة المدخل", "输入预览"),
    ("Delete selected", "حذف انتخاب‌شده‌ها", "حذف المحدد", "删除所选"),
    ("Clear all", "پاک کردن همه", "مسح الكل", "全部清除"),
    ("Refresh", "تازه‌سازی", "تحديث", "刷新"),
    # ---- settings
    ("Language:", "زبان:", "اللغة:", "语言:"),
    ("Theme:", "پوسته:", "السمة:", "主题:"),
    ("Blue (dark)", "آبی (تیره)", "أزرق (داكن)", "蓝色(深色)"),
    ("Green (hacker)", "سبز (هکری)", "أخضر (هاكر)", "绿色(黑客风)"),
    ("Record local history", "ثبت تاریخچه‌ی محلی", "تسجيل السجل المحلي", "记录本地历史"),
    ("Store short input/output previews in history (never for encrypt/decrypt/HMAC)", "ذخیره‌ی پیش‌نمایش کوتاه ورودی/خروجی در تاریخچه (هرگز برای رمزنگاری/رمزگشایی/HMAC)", "حفظ معاينات قصيرة للمدخلات/المخرجات في السجل (أبدًا للتشفير/فك التشفير/HMAC)", "在历史记录中保存简短的输入/输出预览(加密/解密/HMAC 永不保存)"),
    ("Maximum history records:", "حداکثر تعداد رکوردهای تاریخچه:", "أقصى عدد لسجلات السجل:", "历史记录最大条数:"),
    ("Maximum import file size:", "حداکثر حجم فایل ورودی:", "أقصى حجم لملف الاستيراد:", "导入文件大小上限:"),
    ("PBKDF2 iterations (new encryptions):", "تعداد تکرار PBKDF2 (رمزنگاری‌های جدید):", "عدد تكرارات PBKDF2 (للتشفيرات الجديدة):", "PBKDF2 迭代次数(新加密):"),
    ("Clear password field after each Encrypt/Decrypt run", "پاک کردن فیلد رمز عبور پس از هر رمزنگاری/رمزگشایی", "مسح حقل كلمة المرور بعد كل عملية تشفير/فك تشفير", "每次加密/解密后清除密码框"),
    ("Default text encoding:", "کدگذاری پیش‌فرض متن:", "ترميز النص الافتراضي:", "默认文本编码:"),
    ("Enable Persian text scoring in analyzers", "فعال‌سازی امتیازدهی متن فارسی در تحلیلگرها", "تفعيل تقييم النص الفارسي في المحللات", "在分析器中启用波斯语文本评分"),
    ("Persian frequency table:", "جدول بسامد حروف فارسی:", "جدول تكرار الحروف الفارسية:", "波斯语字频表:"),
    ("Browse…", "مرور…", "استعراض…", "浏览…"),
    ("Save settings", "ذخیره‌ی تنظیمات", "حفظ الإعدادات", "保存设置"),
    # ---- main window
    ("File", "فایل", "ملف", "文件"),
    ("Edit", "ویرایش", "تحرير", "编辑"),
    ("Help", "راهنما", "مساعدة", "帮助"),
    ("Import into input…", "وارد کردن به ورودی…", "استيراد إلى المدخل…", "导入到输入…"),
    ("Export output…", "خروجی گرفتن از نتیجه…", "تصدير المخرجات…", "导出输出…"),
    ("Quit", "خروج", "خروج", "退出"),
    ("Run current tab", "اجرای تب فعلی", "تشغيل التبويب الحالي", "运行当前标签页"),
    ("Clear current tab", "پاک کردن تب فعلی", "مسح التبويب الحالي", "清除当前标签页"),
    ("About / offline guarantee", "درباره / تضمین آفلاین بودن", "حول / ضمان العمل دون اتصال", "关于 / 离线保证"),
    ("● OFFLINE · no network access", "● آفلاین · بدون دسترسی به شبکه", "● دون اتصال · لا وصول إلى الشبكة", "● 离线 · 无网络访问"),
    ("Ready. All processing happens locally on this computer.", "آماده. همه‌ی پردازش‌ها روی همین کامپیوتر انجام می‌شود.", "جاهز. تتم كل المعالجة محليًا على هذا الحاسوب.", "就绪。所有处理都在本机完成。"),
    ("CipherLab Pro — offline", "CipherLab Pro — آفلاین", "CipherLab Pro — دون اتصال", "CipherLab Pro — 离线"),
    ("Input: {c} chars · {b} bytes", "ورودی: {c} نویسه · {b} بایت", "المدخل: {c} حرفًا · {b} بايت", "输入:{c} 个字符 · {b} 字节"),
    ("{c} chars · {b} bytes (UTF-8)", "{c} نویسه · {b} بایت (UTF-8)", "{c} حرفًا · {b} بايت (UTF-8)", "{c} 个字符 · {b} 字节 (UTF-8)"),
    ('XOR Encoder', 'رمزگذار XOR', 'مرمّز XOR', 'XOR 编码器'),
    ('XOR Decoder', 'رمزگشای XOR', 'فاكّ XOR', 'XOR 解码器'),
    ('Plaintext', 'متن ساده', 'النص الأصلي', '明文'),
    ('Type or paste the text to encrypt…', 'متنی را که می\u200cخواهید رمز کنید تایپ یا جای\u200cگذاری کنید…', 'اكتب النص المراد تشفيره أو الصقه…', '输入或粘贴要加密的文本…'),
    ('HEX password:', 'رمز هگز:', 'كلمة مرور Hex:', '十六进制密码:'),
    ('Hex digits, e.g. 0xA1B2C3 or 00ff10 (any length, 0x optional)', 'ارقام هگز، مثلاً 0xA1B2C3 یا 00ff10 (هر طولی، 0x اختیاری)', 'خانات Hex، مثلًا 0xA1B2C3 أو 00ff10 (أي طول، و0x اختيارية)', '十六进制数字,例如 0xA1B2C3 或 00ff10(任意长度,0x 可选)'),
    ('Hide', 'پنهان', 'إخفاء', '隐藏'),
    ('Strict: reject odd-length passwords', 'سخت\u200cگیرانه: رد کردن رمزهای با تعداد ارقام فرد', 'صارم: رفض كلمات المرور ذات عدد الخانات الفردي', '严格模式:拒绝位数为奇数的密码'),
    ('Output: bytes separated by spaces', 'خروجی: بایت\u200cها با فاصله', 'المخرجات: البايتات مفصولة بمسافات', '输出:字节以空格分隔'),
    ('Output: continuous', 'خروجی: پیوسته', 'المخرجات: متصلة', '输出:连续'),
    ('Encrypted output (HEX)', 'خروجی رمزشده (هگز)', 'المخرجات المشفّرة (Hex)', '加密输出(十六进制)'),
    ('Repeating-key XOR is NOT secure encryption. Use it for learning and simple obfuscation only.', 'XOR با کلید تکرارشونده رمزنگاری امن نیست. فقط برای یادگیری و مبهم\u200cسازی ساده از آن استفاده کنید.', 'XOR بمفتاح متكرر ليس تشفيرًا آمنًا. استخدمه للتعلّم والتعتيم البسيط فقط.', '重复密钥 XOR 不是安全的加密,仅用于学习和简单混淆。'),
    ('Encrypted HEX data', 'داده\u200cی هگز رمزشده', 'بيانات Hex المشفّرة', '加密的十六进制数据'),
    ('Paste the encrypted HEX output…', 'خروجی هگز رمزشده را جای\u200cگذاری کنید…', 'الصق مخرجات Hex المشفّرة…', '粘贴加密后的十六进制输出…'),
    ('Decrypted text (UTF-8)', 'متن رمزگشایی\u200cشده (UTF-8)', 'النص بعد فك التشفير (UTF-8)', '解密后的文本(UTF-8)'),
    ('XOR has no integrity check: a wrong password gives different bytes, and only valid UTF-8 can be shown as text.', 'XOR بررسی صحت ندارد: رمز اشتباه بایت\u200cهای متفاوتی می\u200cدهد و فقط UTF-8 معتبر به صورت متن نمایش داده می\u200cشود.', 'لا يملك XOR فحصًا للسلامة: كلمة المرور الخاطئة تعطي بايتات مختلفة، ولا يمكن عرض إلا UTF-8 الصالح كنص.', 'XOR 没有完整性校验:密码错误会得到不同的字节,只有有效的 UTF-8 才能显示为文本。'),
    ('Enter a HEX password (digits 0-9, a-f)', 'یک رمز هگز وارد کنید (ارقام 0-9 و a-f)', 'أدخل كلمة مرور Hex (الأرقام 0-9 وa-f)', '请输入十六进制密码(数字 0-9、字母 a-f)'),
    ('Password OK: {n} byte(s), {m} hex digits. Key bytes: {k}', 'رمز معتبر است: {n} بایت، {m} رقم هگز. بایت\u200cهای کلید: {k}', 'كلمة المرور صالحة: {n} بايت، {m} خانة Hex. بايتات المفتاح: {k}', '密码有效:{n} 字节,{m} 个十六进制位。密钥字节:{k}'),
    ('A leading 0 was added because the digit count is odd (like 0x474 = 0x0474).', 'چون تعداد ارقام فرد است، یک صفر در ابتدا اضافه شد (مثل 0x474 = 0x0474).', 'أُضيف صفر في البداية لأن عدد الخانات فردي (مثل 0x474 = 0x0474).', '由于位数为奇数,已在前面补一个 0(如 0x474 = 0x0474)。'),
]


# English -> Russian (kept separate so the 4-column table above stays untouched)
_RU: dict[str, str] = {
    "Encode": "Кодирование", "Decode": "Декодирование", "Encrypt": "Шифрование", "Decrypt": "Расшифровка",
    "Hex Analyzer": "Hex-анализ", "XOR Analyzer": "XOR-анализ", "Compare Results": "Сравнение",
    "History": "История", "About": "О программе", "Settings": "Настройки",
    "Paste": "Вставить", "Copy": "Копировать", "Clear": "Очистить", "Import…": "Импорт…", "Export…": "Экспорт…",
    "Analyze": "Анализ", "Cancel": "Отмена", "Run": "Выполнить", "Show": "Показать",
    "Replace the content with the clipboard text": "Заменить содержимое текстом из буфера обмена",
    "Copy to the clipboard": "Копировать в буфер обмена",
    "Clear this editor": "Очистить это поле",
    "Load a TXT / HEX / JSON / binary file (or drop one here)": "Загрузить файл TXT / HEX / JSON / двоичный (или перетащите его сюда)",
    "Save the content to a file": "Сохранить содержимое в файл",
    "Text to encode": "Текст для кодирования", "Encoded result": "Результат кодирования",
    "Encoded input": "Закодированные данные", "Decoded result": "Результат декодирования",
    "Plaintext / message": "Открытый текст / сообщение", "Result": "Результат",
    "Encrypted data": "Зашифрованные данные", "Decrypted result": "Результат расшифровки",
    "Hexadecimal input": "Шестнадцатеричный ввод", "Input bytes": "Входные байты",
    "Type or paste text (Persian, Arabic, English, emoji…)": "Введите или вставьте текст (персидский, арабский, английский, эмодзи…)",
    "Message to encrypt or hash": "Сообщение для шифрования или хеширования",
    "Password (never saved or logged)": "Пароль (никогда не сохраняется и не записывается в журнал)",
    "Key (never saved or logged)": "Ключ (никогда не сохраняется и не записывается в журнал)",
    "Paste the CipherLab Pro JSON container (or XOR hex)": "Вставьте JSON-контейнер CipherLab Pro (или XOR в hex)",
    "Raw key (AES key-mode / XOR; never saved or logged)": "Исходный ключ (режим ключа AES / XOR; никогда не сохраняется и не записывается в журнал)",
    "Ciphertext as hex (or switch to UTF-8 text)": "Шифртекст в hex (или переключитесь на текст UTF-8)",
    "Known key (never saved)": "Известный ключ (не сохраняется)",
    "Search history…": "Поиск по истории…",
    "The analysis report appears here.": "Отчёт об анализе появится здесь.",
    "Key-length ranking appears here.": "Рейтинг длины ключа появится здесь.",
    "Select a candidate to see how it was scored.": "Выберите вариант, чтобы увидеть, как он оценивался.",
    "Text encoding:": "Кодировка текста:", "Output format:": "Формат вывода:",
    "Hex separator: space": "Разделитель hex: пробел", "Hex separator: none": "Разделитель hex: нет",
    "Uppercase hex": "Hex заглавными", "Hexadecimal": "Шестнадцатеричный",
    "URL (percent) encoding": "URL-кодирование (процентное)",
    "Unicode escape (\\uXXXX)": "Escape-последовательности Unicode (\\uXXXX)",
    "JSON string escape": "Экранирование строки JSON", "Binary (8-bit groups)": "Двоичный (группы по 8 бит)",
    "Decimal bytes": "Десятичные байты", "Input format:": "Формат ввода:",
    "Interpret bytes as:": "Интерпретировать байты как:",
    "Strict: report invalid bytes": "Строго: сообщать о неверных байтах",
    "Replace invalid bytes with U+FFFD (lossy)": "Заменять неверные байты на U+FFFD (с потерями)",
    "Suggest format": "Определить формат",
    "List the formats the input could be written in (ambiguity is reported, not hidden)": "Показать форматы, в которых может быть записан ввод (неоднозначность показывается, а не скрывается)",
    "Raw bytes as hexadecimal (no text decoding)": "Исходные байты в hex (без декодирования текста)",
    "Algorithm:": "Алгоритм:", "AES-256-GCM (password)": "AES-256-GCM (пароль)",
    "AES-GCM (raw key, hex)": "AES-GCM (исходный ключ, hex)",
    "Repeating-key XOR (educational, NOT secure)": "XOR с повторяющимся ключом (учебный, НЕ безопасен)",
    "SHA-256 hash (not encryption)": "Хеш SHA-256 (не шифрование)",
    "SHA-512 hash (not encryption)": "Хеш SHA-512 (не шифрование)",
    "HMAC-SHA256 (authentication, not encryption)": "HMAC-SHA256 (аутентификация, не шифрование)",
    "HMAC-SHA512 (authentication, not encryption)": "HMAC-SHA512 (аутентификация, не шифрование)",
    "Input is UTF-8 text": "Ввод — текст UTF-8", "Input is hexadecimal bytes": "Ввод — байты в шестнадцатеричном виде",
    "Key as text": "Ключ как текст", "Key as hex": "Ключ в hex",
    "XOR with a repeating key is trivially breakable. Use it only to learn how XOR works.": "XOR с повторяющимся ключом легко взламывается. Используйте его только для изучения принципа работы XOR.",
    "A hash is one-way and cannot be decrypted. It is neither encryption nor encoding.": "Хеш односторонний и не подлежит расшифровке. Это не шифрование и не кодирование.",
    "HMAC proves integrity/authenticity with a secret key; it does not hide the message.": "HMAC подтверждает целостность и подлинность с помощью секретного ключа; он не скрывает сообщение.",
    "AES-GCM container (JSON from the Encrypt tab)": "Контейнер AES-GCM (JSON с вкладки «Шифрование»)",
    "Repeating-key XOR (input as hex)": "XOR с повторяющимся ключом (ввод в hex)",
    "Include bounded repeating-key XOR analysis": "Включить ограниченный анализ XOR с повторяющимся ключом",
    "Input is hexadecimal": "Ввод — шестнадцатеричный", "Single-byte XOR analysis": "Анализ однобайтового XOR",
    "Repeating-key XOR analysis (bounded)": "Анализ XOR с повторяющимся ключом (ограниченный)",
    "max key length": "макс. длина ключа", "top": "топ", "Apply key": "Применить ключ",
    "XOR is not secure encryption. Results are statistical guesses; readable output is evidence, not proof.": "XOR — не безопасное шифрование. Результаты — статистические догадки; читаемый вывод — свидетельство, а не доказательство.",
    "Method": "Метод", "Score": "Оценка", "Confidence": "Уверенность", "Printable": "Печатные", "Errors": "Ошибки",
    "Copy output (text)": "Копировать вывод (текст)", "Copy output (hex)": "Копировать вывод (hex)",
    "Send selected to Compare": "Отправить выбранное на сравнение", "Send all to Compare": "Отправить всё на сравнение",
    "Copy the decoded text of the selected candidate": "Копировать декодированный текст выбранного варианта",
    "Copy the full output bytes as hexadecimal": "Копировать все выходные байты в hex",
    "Add the selected candidates to the Compare Results tab": "Добавить выбранные варианты на вкладку «Сравнение»",
    "Add every candidate to the Compare Results tab": "Добавить все варианты на вкладку «Сравнение»",
    "Send candidates here from the Hex Analyzer or XOR Analyzer tabs to compare them side by side.": "Отправляйте сюда варианты с вкладок «Hex-анализ» или «XOR-анализ», чтобы сравнить их рядом.",
    "Remove selected column": "Удалить выбранный столбец", "Export JSON…": "Экспорт JSON…",
    "Quality × prior": "Качество × априорная вероятность", "Printable ratio": "Доля печатных",
    "Decoding errors": "Ошибки декодирования", "Entropy (bits/byte)": "Энтропия (бит/байт)",
    "Key (hex)": "Ключ (hex)", "Output preview": "Предпросмотр вывода", "Why": "Причина",
    "Record history": "Вести историю", "Time (UTC)": "Время (UTC)", "Operation": "Операция", "Summary": "Сводка",
    "Input preview": "Предпросмотр ввода", "Delete selected": "Удалить выбранное", "Clear all": "Очистить всё",
    "Refresh": "Обновить",
    "Theme:": "Тема:", "Blue (dark)": "Синяя (тёмная)", "Green (hacker)": "Зелёная (хакерская)",
    "Language:": "Язык:", "Record local history": "Вести локальную историю",
    "Store short input/output previews in history (never for encrypt/decrypt/HMAC)": "Хранить в истории краткие превью ввода/вывода (никогда для шифрования/расшифровки/HMAC)",
    "Maximum history records:": "Максимум записей истории:",
    "Maximum import file size:": "Максимальный размер импортируемого файла:",
    "PBKDF2 iterations (new encryptions):": "Итерации PBKDF2 (для новых шифрований):",
    "Clear password field after each Encrypt/Decrypt run": "Очищать поле пароля после каждого шифрования/расшифровки",
    "Default text encoding:": "Кодировка текста по умолчанию:",
    "Enable Persian text scoring in analyzers": "Включить оценку персидского текста в анализаторах",
    "Persian frequency table:": "Таблица частот персидских букв:", "Browse…": "Обзор…",
    "Save settings": "Сохранить настройки",
    "File": "Файл", "Edit": "Правка", "Help": "Справка", "Import into input…": "Импорт во ввод…",
    "Export output…": "Экспорт вывода…", "Quit": "Выход", "Run current tab": "Выполнить текущую вкладку",
    "Clear current tab": "Очистить текущую вкладку",
    "About / offline guarantee": "О программе / гарантия работы офлайн",
    "● OFFLINE · no network access": "● ОФЛАЙН · нет доступа к сети",
    "Ready. All processing happens locally on this computer.": "Готово. Вся обработка выполняется локально на этом компьютере.",
    "CipherLab Pro — offline": "CipherLab Pro — офлайн",
    "Input: {c} chars · {b} bytes": "Ввод: {c} симв. · {b} байт",
    "{c} chars · {b} bytes (UTF-8)": "{c} симв. · {b} байт (UTF-8)",
    'XOR Encoder': 'XOR-шифратор',
    'XOR Decoder': 'XOR-расшифровщик',
    'Plaintext': 'Открытый текст',
    'Type or paste the text to encrypt…': 'Введите или вставьте текст для шифрования…',
    'HEX password:': 'HEX-пароль:',
    'Hex digits, e.g. 0xA1B2C3 or 00ff10 (any length, 0x optional)': 'Hex-цифры, например 0xA1B2C3 или 00ff10 (любая длина, 0x необязательно)',
    'Hide': 'Скрыть',
    'Strict: reject odd-length passwords': 'Строго: отклонять пароли с нечётным числом цифр',
    'Output: bytes separated by spaces': 'Вывод: байты через пробел',
    'Output: continuous': 'Вывод: слитно',
    'Encrypted output (HEX)': 'Зашифрованный вывод (HEX)',
    'Repeating-key XOR is NOT secure encryption. Use it for learning and simple obfuscation only.': 'XOR с повторяющимся ключом — НЕ безопасное шифрование. Используйте его только для обучения и простой обфускации.',
    'Encrypted HEX data': 'Зашифрованные HEX-данные',
    'Paste the encrypted HEX output…': 'Вставьте зашифрованный HEX-вывод…',
    'Decrypted text (UTF-8)': 'Расшифрованный текст (UTF-8)',
    'XOR has no integrity check: a wrong password gives different bytes, and only valid UTF-8 can be shown as text.': 'У XOR нет проверки целостности: неверный пароль даёт другие байты, а как текст можно показать только корректный UTF-8.',
    'Enter a HEX password (digits 0-9, a-f)': 'Введите HEX-пароль (цифры 0-9, a-f)',
    'Password OK: {n} byte(s), {m} hex digits. Key bytes: {k}': 'Пароль корректен: {n} байт, {m} hex-цифр. Байты ключа: {k}',
    'A leading 0 was added because the digit count is odd (like 0x474 = 0x0474).': 'Добавлен ведущий 0, так как число цифр нечётное (как 0x474 = 0x0474).',
}

def _zh_punct(text: str) -> str:
    """Use full-width Chinese punctuation for ':' '(' ')' (placeholders like {c} are untouched)."""
    return text.replace("(", "（").replace(")", "）").replace(":", "：")


_TABLE: dict[str, dict[str, str]] = {"fa": {}, "ar": {}, "zh": {}, "ru": dict(_RU)}
for _en, _fa, _ar, _zh in _ROWS:
    _TABLE["fa"][_en], _TABLE["ar"][_en], _TABLE["zh"][_en] = _fa, _ar, _zh_punct(_zh)

_current = "en"


def known_sources() -> set[str]:
    return {row[0] for row in _ROWS}


def current_language() -> str:
    return _current


def set_language(lang: str) -> str:
    global _current
    _current = lang if lang in LANGS else "en"
    return _current


def translate(text: str, lang: str) -> str:
    """Translate an English UI string; unknown strings are returned unchanged."""
    if lang == "en" or not text:
        return text
    stripped = text.strip()
    found = _TABLE.get(lang, {}).get(stripped.replace("&", ""))
    if found is None:
        return text
    lead = text[: len(text) - len(text.lstrip())]
    trail = text[len(text.rstrip()):]
    return lead + found + trail


def tr(text: str) -> str:
    """Translate using the currently selected language."""
    return translate(text, _current)


# ---------------------------------------------------------------- widget-tree walker
Item = tuple[object, str, Callable[[], str], Callable[[str], None]]


def _menu_items(menu_or_bar) -> Iterator[Item]:
    for act in menu_or_bar.actions():
        yield act, "text", act.text, act.setText
        sub = act.menu()
        if sub is not None:
            yield from _menu_items(sub)


def iter_items(root: QWidget) -> Iterator[Item]:
    """Yield every (object, key, getter, setter) for translatable text under ``root``."""
    for w in [root, *root.findChildren(QWidget)]:
        if isinstance(w, QLabel):
            yield w, "text", w.text, w.setText
        elif isinstance(w, QAbstractButton):
            yield w, "text", w.text, w.setText
        elif isinstance(w, QComboBox):
            for i in range(w.count()):
                yield w, f"item{i}", (lambda w=w, i=i: w.itemText(i)), (lambda v, w=w, i=i: w.setItemText(i, v))
        elif isinstance(w, QSpinBox):
            yield w, "prefix", w.prefix, w.setPrefix
            yield w, "suffix", w.suffix, w.setSuffix
        elif isinstance(w, QTabWidget):
            for i in range(w.count()):
                yield w, f"tab{i}", (lambda w=w, i=i: w.tabText(i)), (lambda v, w=w, i=i: w.setTabText(i, v))
        elif isinstance(w, QTableWidget):
            for i in range(w.columnCount()):
                it = w.horizontalHeaderItem(i)
                if it is not None:
                    yield w, f"h{i}", it.text, it.setText
            for i in range(w.rowCount()):
                it = w.verticalHeaderItem(i)
                if it is not None:
                    yield w, f"v{i}", it.text, it.setText
        if isinstance(w, (QLineEdit, QPlainTextEdit)):
            yield w, "placeholder", w.placeholderText, w.setPlaceholderText
        if w.toolTip():
            yield w, "tip", w.toolTip, w.setToolTip
        if isinstance(w, QMainWindow):
            yield w, "wtitle", w.windowTitle, w.setWindowTitle
            yield from _menu_items(w.menuBar())


def _sync(obj, key: str, get: Callable[[], str], set_: Callable[[str], None], lang: str) -> None:
    cur = get()
    if not cur:
        return
    p_src, p_app = f"_i18n_src_{key}", f"_i18n_app_{key}"
    src, applied = obj.property(p_src), obj.property(p_app)
    if src is None or cur != applied:  # first visit, or program code wrote new text
        src = cur
    new = translate(src, lang)
    if new != cur:
        set_(new)
    obj.setProperty(p_src, src)
    obj.setProperty(p_app, new)


def retranslate(root: QWidget, lang: str) -> None:
    """Apply ``lang`` to the whole widget tree and switch layout direction (RTL for fa/ar)."""
    lang = set_language(lang)
    app = QApplication.instance()
    if app is not None:
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft if lang in RTL_LANGS else Qt.LayoutDirection.LeftToRight)
    for obj, key, get, set_ in list(iter_items(root)):
        _sync(obj, key, get, set_, lang)


def english_sources(root: QWidget) -> set[str]:
    """All current (English) UI texts under ``root`` - used by the coverage test."""
    return {get() for _o, _k, get, _s in iter_items(root) if get()}
