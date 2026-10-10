# -*- coding: utf-8 -*-
"""
مرجع بوينغ الهندسي 2004–2010 — نموذج أولي بـ Streamlit
التثبيت:  pip install streamlit pandas plotly
التشغيل:  streamlit run boeing_app.py

مصدر البيانات: ملف Boeing_2004_2010.pdf (مواصفات الطرازات، حالة البرامج، الأحداث والملاحظات الهندسية).
تنبيه: الملف لا يحتوي أرقام تسجيل ولا سجلات صيانة؛ فصل ATA والنظام الفرعي في السجلات
تصنيف تحليلي وُضع هنا استناداً إلى نص كل ملاحظة، وليس حقلاً موجوداً في المصدر.
"""
from datetime import datetime
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="مرجع بوينغ الهندسي 2004–2010", page_icon="✈️", layout="wide")

ALL = "جميع الطرازات"
YEARS = list(range(2004, 2011))
_NEW_API = tuple(int(p) for p in st.__version__.split(".")[:2]) >= (1, 50)

# ───────────────────────── تنسيق (RTL) ─────────────────────────
st.markdown(
    """
<style>
.stApp, [data-testid="stSidebar"], [data-testid="stMarkdownContainer"], label, .stTabs, .streamlit-expanderHeader,
[data-testid="stMetric"], [data-testid="stExpander"], [data-testid="stForm"], .stAlert { direction: rtl; text-align: right; }
html, body, .stApp, input, textarea, button { font-family: "Tahoma","Segoe UI","Noto Naskh Arabic",sans-serif !important; }
[data-testid="stDataFrame"], .js-plotly-plot, .stSlider { direction: ltr; }
[data-testid="stMetric"] { background:#F4F7FA; border:1px solid #D5DEE8; border-radius:10px; padding:12px 16px; }
[data-testid="stMetricLabel"] { justify-content:flex-start; }
h1, h2, h3 { color:#1F3A5F; }
input, textarea { direction: rtl; text-align: right; }
</style>
""",
    unsafe_allow_html=True,
)

# ───────────────────────── البيانات المضمّنة ─────────────────────────
ATA = {
    "00": ("معلومات عامة", "نظرة عامة على البرامج والطرازات ومعالمها (إطلاق، طرح، تحليق، خدمة، تأخيرات)."),
    "05": ("الحدود الزمنية وفحوص الصيانة", "فترات الفحص والصيانة المجدولة وبرامج الدعم."),
    "21": ("التكييف والتحكم الحراري", "تكييف المقصورة والضغط والتحكم الحراري في الشحن."),
    "22": ("الطيار الآلي", "أنظمة الطيران الآلي والتحكم في المسار."),
    "23": ("الاتصالات", "أنظمة الاتصال الصوتي والبيانات."),
    "24": ("القدرة الكهربائية", "التوليد والتوزيع الكهربائي وحماية الدوائر."),
    "25": ("التجهيزات والمقصورة", "المقاعد والمطابخ ومعدات المقصورة."),
    "26": ("الحماية من الحريق", "كشف الحريق وإطفاؤه."),
    "27": ("أسطح التحكم بالطيران", "الجنيحات والمصاعد والدفة وأنظمة Fly-by-Wire."),
    "28": ("الوقود", "الخزانات ونقل الوقود وسعاته."),
    "29": ("القدرة الهيدروليكية", "المضخات والدوائر الهيدروليكية."),
    "30": ("الحماية من الجليد والمطر", "إزالة الجليد وماسحات الزجاج."),
    "31": ("أجهزة القياس والعرض", "قمرة القيادة وشاشات EFIS ومسجلات الطيران."),
    "32": ("معدات الهبوط", "العجلات والمكابح والدعامات وأنظمة الجر."),
    "34": ("الملاحة", "أنظمة الملاحة والمعدات اللاسلكية."),
    "36": ("الهواء المضغوط (Bleed Air)", "سحب الهواء من المحركات وتوزيعه."),
    "38": ("المياه والنفايات", "أنظمة المياه الصالحة للشرب ودورات المياه."),
    "45": ("نظام الصيانة المركزي", "المراقبة والتشخيص المركزي."),
    "46": ("أنظمة المعلومات", "شبكات البيانات (مثل ARINC 629) وأنظمة المعلومات."),
    "49": ("وحدة القدرة المساعدة (APU)", "وحدة الطاقة المساعدة وملحقاتها."),
    "50": ("عنابر الشحن والملحقات", "الأرضيات وتجهيزات الشحن والتحميل والتفريغ."),
    "51": ("الهيكل العام والمواد", "المواد الإنشائية (ألمنيوم، تيتانيوم، مركبات) والمثبتات."),
    "52": ("الأبواب", "أبواب الركاب والطوارئ والشحن."),
    "53": ("جسم الطائرة", "الأقسام الإنشائية للجسم (Fuselage / Barrel)."),
    "54": ("الحوامل والأغلفة (Nacelles/Pylons)", "تثبيت المحركات وأغلفتها."),
    "55": ("المثبتات (الذيل)", "المثبت الأفقي والعمودي والذيل."),
    "56": ("النوافذ", "نوافذ المقصورة وقمرة القيادة."),
    "57": ("الأجنحة", "الجناح وصندوق الجناح والأطراف وWinglets ووصلة الجناح بالجسم."),
    "71": ("محطة القدرة", "تركيب المحرك والغلاف والتجهيزات العامة."),
    "72": ("المحرك", "المحركات التوربينية (مروحة، ضاغط، احتراق، توربين)."),
    "73": ("التحكم بوقود المحرك", "وحدات التحكم الرقمي بالمحرك ووقوده."),
    "74": ("الإشعال", "أنظمة إشعال المحرك."),
    "75": ("هواء المحرك", "تبريد وتحكم هواء المحرك."),
    "77": ("مؤشرات المحرك", "قياس ومراقبة أداء المحرك."),
    "78": ("العادم", "العادم وعكس الدفع."),
    "79": ("زيت المحرك", "نظام الزيت."),
    "80": ("بدء التشغيل", "أنظمة بدء تشغيل المحرك."),
}
ATA_GROUPS = {
    "عام (00–12)": ["00", "05"],
    "أنظمة الطائرة (21–49)": ["21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "34", "36", "38", "45", "46", "49"],
    "الهيكل (50–57)": ["50", "51", "52", "53", "54", "55", "56", "57"],
    "المحركات (71–80)": ["71", "72", "73", "74", "75", "77", "78", "79", "80"],
}

CATS = ["ملاحظة تصميمية", "حدث/مرحلة", "تأخير", "مشكلة فنية", "مخطط", "ملاحظة صيانة"]
STATUS_OPTIONS = ["مرجعي", "مكتمل", "مخطط", "تأخير مسجّل", "مشكلة موثّقة", "قيد المتابعة", "مغلق"]
STATUS_BY_CAT = {"ملاحظة تصميمية": "مرجعي", "حدث/مرحلة": "مكتمل", "تأخير": "تأخير مسجّل",
                 "مشكلة فنية": "مشكلة موثّقة", "مخطط": "مخطط", "ملاحظة صيانة": "قيد المتابعة"}

MODEL_ROWS = [
    ('717-200', '717', '717', 'ضيق البدن', 'ركاب', 2005, 37.8, 28.45, 31750, 49900, None, None, 0.77),
    ('737-300', '737 Classic', '737', 'ضيق البدن', 'ركاب', 2004, 33.4, 28.88, None, 63277, None, 4973, 0.745),
    ('737-400', '737 Classic', '737', 'ضيق البدن', 'ركاب', 2004, 36.4, 28.88, 33643, 68039, 16000, 4000, None),
    ('737-500', '737 Classic', '737', 'ضيق البدن', 'ركاب', 2004, 31.01, 28.88, None, 61689, None, 4444, 0.745),
    ('737-600', '737NG', '737', 'ضيق البدن', 'ركاب', 2004, 31.24, 34.31, 37104, 65090, None, 5648, None),
    ('737-700', '737NG', '737', 'ضيق البدن', 'ركاب', 2004, 33.63, 34.31, 38147, 70080, None, 6037, None),
    ('737-800', '737NG', '737', 'ضيق البدن', 'ركاب', 2004, 39.47, 35.79, 41145, 79015, 20865, 5665, 0.78),
    ('737-900', '737NG', '737', 'ضيق البدن', 'ركاب', 2004, 42.11, 35.79, 42493, 79015, 21300, 5080, None),
    ('737-900ER', '737NG', '737', 'ضيق البدن', 'ركاب', 2008, 42.11, 35.79, 44676, 85139, 23045, 5925, None),
    ('747-400', '747-400', '747', 'عريض البدن', 'ركاب', 2004, 70.67, 64.44, 178800, 396893, 63955, 13492, 0.85),
    ('747-8F', '747-8', '747', 'عريض البدن', 'شحن', 2010, 76.3, None, None, 442000, None, None, None),
    ('747-8I', '747-8', '747', 'عريض البدن', 'ركاب', 2009, 76.0, None, None, 442000, None, None, None),
    ('757-200', '757', '757', 'ضيق البدن', 'ركاب', 2004, 47.32, 38.05, 57840, 115680, 31300, 7222, 0.8),
    ('757-300', '757', '757', 'ضيق البدن', 'ركاب', 2004, 54.4, 38.05, None, 123600, None, 6300, 0.8),
    ('767-200ER', '767', '767', 'عريض البدن', 'ركاب', 2004, 48.51, 47.6, None, 179169, None, 12350, 0.8),
    ('767-300ER', '767', '767', 'عريض البدن', 'ركاب', 2004, 54.94, 47.57, 86070, 187000, 44700, 10603, 0.86),
    ('767-300F', '767', '767', 'عريض البدن', 'شحن', 2008, 54.94, 47.58, 90000, 186880, 52500, 6025, 0.86),
    ('767-400ER', '767', '767', 'عريض البدن', 'ركاب', 2004, 61.37, None, None, None, None, 10400, 0.8),
    ('777-200ER', '777', '777', 'عريض البدن', 'ركاب', 2004, 63.7, 60.9, 138100, 299000, 53000, 14305, 0.84),
    ('777-200LR', '777', '777', 'عريض البدن', 'ركاب', 2005, 63.73, 64.8, 145150, 347450, 52600, 17445, 0.84),
    ('777-300', '777', '777', 'عريض البدن', 'ركاب', 2004, 73.9, 60.93, None, 299000, None, 11125, None),
    ('777-300ER', '777', '777', 'عريض البدن', 'ركاب', 2004, 73.9, 64.8, 167829, 351534, 68000, 15840, 0.84),
    ('777F', '777', '777', 'عريض البدن', 'شحن', 2009, 63.73, 64.8, 145150, 347815, 102010, 9070, 0.84),
    ('787-8', '787', '787', 'عريض البدن', 'ركاب', 2004, 57.0, 60.0, None, None, None, 15700, 0.85),
]
MODELS = pd.DataFrame(MODEL_ROWS, columns=["model", "program", "family", "body", "kind", "first_year", "length_m",
                                           "wingspan_m", "oew_kg", "mtow_kg", "payload_kg", "range_km", "mach"])

STATUS_ROWS = [
    ('717', 2005, 'IN_PRODUCTION'),
    ('737 Classic', 2004, 'OUT_OF_PRODUCTION'),
    ('737 Classic', 2006, 'OUT_OF_PRODUCTION'),
    ('737NG', 2004, 'IN_PRODUCTION'),
    ('737NG', 2005, 'IN_PRODUCTION'),
    ('737NG', 2006, 'IN_PRODUCTION'),
    ('737NG', 2007, 'IN_PRODUCTION'),
    ('737NG', 2008, 'IN_PRODUCTION'),
    ('737NG', 2009, 'IN_PRODUCTION'),
    ('737NG', 2010, 'IN_PRODUCTION'),
    ('747-400', 2004, 'IN_PRODUCTION'),
    ('747-400', 2005, 'IN_PRODUCTION'),
    ('747-400', 2006, 'IN_PRODUCTION'),
    ('747-400', 2007, 'IN_PRODUCTION'),
    ('747-400', 2008, 'IN_PRODUCTION'),
    ('747-400', 2009, 'IN_PRODUCTION'),
    ('747-400', 2010, 'IN_PRODUCTION'),
    ('747-8', 2007, 'DEVELOPMENT'),
    ('747-8', 2008, 'DEVELOPMENT'),
    ('747-8', 2009, 'DEVELOPMENT'),
    ('747-8', 2010, 'FLIGHT_TEST'),
    ('757', 2004, 'OUT_OF_PRODUCTION'),
    ('757', 2005, 'OUT_OF_PRODUCTION'),
    ('757', 2006, 'OUT_OF_PRODUCTION'),
    ('757', 2007, 'OUT_OF_PRODUCTION'),
    ('767', 2004, 'IN_PRODUCTION'),
    ('767', 2005, 'IN_PRODUCTION'),
    ('767', 2006, 'IN_PRODUCTION'),
    ('767', 2007, 'IN_PRODUCTION'),
    ('767', 2008, 'IN_PRODUCTION'),
    ('767', 2009, 'IN_PRODUCTION'),
    ('767', 2010, 'IN_PRODUCTION'),
    ('777', 2004, 'IN_PRODUCTION'),
    ('777', 2005, 'IN_PRODUCTION'),
    ('777', 2006, 'IN_PRODUCTION'),
    ('777', 2007, 'IN_PRODUCTION'),
    ('777', 2008, 'IN_PRODUCTION'),
    ('777', 2009, 'IN_PRODUCTION'),
    ('777', 2010, 'IN_PRODUCTION'),
    ('787', 2004, 'DEVELOPMENT'),
    ('787', 2005, 'DEVELOPMENT'),
    ('787', 2006, 'DEVELOPMENT'),
    ('787', 2007, 'DEVELOPMENT'),
    ('787', 2008, 'DEVELOPMENT'),
    ('787', 2009, 'FLIGHT_TEST'),
    ('787', 2010, 'FLIGHT_TEST'),
]
PROG_STATUS = pd.DataFrame(STATUS_ROWS, columns=["program", "year", "status"])
STATUS_AR = {"DEVELOPMENT": "تطوير", "FLIGHT_TEST": "اختبار طيران", "IN_PRODUCTION": "إنتاج", "OUT_OF_PRODUCTION": "توقف الإنتاج"}
STATUS_CODE = {"DEVELOPMENT": 0, "FLIGHT_TEST": 1, "IN_PRODUCTION": 2, "OUT_OF_PRODUCTION": 3}

D, E, L, I = "ملاحظة تصميمية", "حدث/مرحلة", "تأخير", "مشكلة فنية"
RECORDS = [
 (2004, ALL, "737 Classic", "72", "المحركات", D, "محركات CFM56-3 عالية الالتفاف بقطر مروحة ≈60 بوصة ونسبة التفاف ≈5:1", 2),
 (2004, ALL, "737 Classic", "31", "قمرة القيادة", D, "إلكترونيات هجينة (تناظرية/رقمية) بطاقم من طيارين دون مهندس طيران", 2),
 (2004, ALL, "737NG", "72", "المحركات", D, "CFM56-7B بدفع يصل إلى ≈27,300 رطل ونسبة التفاف ≈5.1:1", 3),
 (2004, ALL, "737NG", "57", "الجناح", D, "جناح بمقطع هوائي جديد: زاد الباع ≈4.9 م والمساحة ≈25% (125 م²) وانحناء ≈25°", 3),
 (2004, ALL, "737NG", "31", "قمرة القيادة", D, "ست شاشات LCD بنظام EFIS وتصميم إلكتروني قريب من فلسفة 777", 3),
 (2004, "747-400", "747-400", "72", "المحركات", D, "PW4000 أو CF6-80C2 أو RB211-524G/H بدفع حتى ≈62,000 رطل", 4),
 (2004, "747-400", "747-400", "28", "الوقود", D, "سعة الوقود ≈216,840 لتر", 4),
 (2004, "747-400", "747-400", "31", "قمرة القيادة", D, "Glass Cockpit بطاقم من طيارين اثنين دون مهندس طيران", 4),
 (2004, ALL, "757", "57", "الجناح", D, "جناح Supercritical بمساحة ≈185 م² وانحناء ≈25° لتقليل السحب", 5),
 (2004, ALL, "757", "72", "المحركات", D, "RB211-535 أو PW2000 بدفع حتى ≈43,500 رطل", 5),
 (2004, ALL, "767", "72", "المحركات", D, "محركات Pratt & Whitney وGeneral Electric وRolls-Royce بدفع حتى ≈57,900 رطل", 6),
 (2004, ALL, "777", "72", "المحركات", D, "GE90 وPW4000 وTrent 800؛ و777-300ER حصرياً GE90-115B بدفع ≈115,000 رطل", 7),
 (2004, "777-300ER", "777", "57", "الجناح", D, "أطراف جناح مائلة (Raked Wingtips) وانحناء ≈31.6°", 7),
 (2004, ALL, "777", "27", "أسطح التحكم", D, "نظام تحكم Fly-by-Wire كامل", 7),
 (2004, ALL, "777", "46", "شبكة البيانات", D, "إلكترونيات متقدمة وشبكة بيانات ARINC 629", 7),
 (2004, "787-8", "787", "51", "الهيكل والمواد", D, "استهداف مواد مركبة ≈50% من وزن الهيكل (مشروع 7E7)", 8),
 (2004, "747-400", "747-400", "00", "عام", E, "دخول 747-400ER الخدمة خلال الفترة", 4),
 (2004, ALL, "757", "00", "عام", E, "انتهاء إنتاج 757 وتسليم آخر طائرة", 15),
 (2004, "777-300ER", "777", "00", "عام", E, "دخول 777-300ER الخدمة", 7),
 (2004, "787-8", "787", "00", "عام", E, "موافقة بوينغ على إطلاق 7E7 بعد طلبية ANA لـ50 طائرة (أبريل 2004)", 8),
 (2005, "717-200", "717", "72", "المحركات", D, "محركان Rolls-Royce BR715 (18,500–20,000 رطل) مثبتان في مؤخرة الجسم", 12),
 (2005, "717-200", "717", "55", "الذيل", D, "ذيل على شكل T", 12),
 (2005, ALL, "737NG", "72", "المحركات", D, "CFM56-7B بدفع ≈19,500–27,300 رطل", 13),
 (2005, ALL, "737NG", "27", "أسطح التحكم", D, "قمرة رقمية EFIS بست شاشات LCD دون نظام Fly-by-Wire كامل", 13),
 (2005, "777-200LR", "777", "57", "الجناح", D, "جناح محسّن مع أطراف Extended/Raked Wingtips", 17),
 (2005, "777-200LR", "777", "28", "الوقود", D, "زيادة سعة الوقود", 17),
 (2005, "777-200LR", "777", "32", "معدات الهبوط", D, "تحسينات في معدات الهبوط والهيكل", 17),
 (2005, "777-200LR", "777", "72", "المحركات", D, "GE90-110B/GE90-115B بدفع يصل إلى ≈115,000 رطل", 17),
 (2005, "787-8", "787", "27", "أسطح التحكم", D, "الاعتماد على Fly-by-Wire", 18),
 (2005, "787-8", "787", "24", "القدرة الكهربائية", D, "زيادة استخدام الأنظمة الكهربائية وتقليل الاعتماد على الهيدروليكية التقليدية", 18),
 (2005, "787-8", "787", "51", "الهيكل والمواد", D, "مواد مركبة ≈50% (ألمنيوم ≈20%، تيتانيوم ≈15%، فولاذ ≈10%)", 18),
 (2005, "787-8", "787", "72", "المحركات", D, "General Electric GEnx أو Rolls-Royce Trent 1000", 18),
 (2005, "787-8", "787", "53", "جسم الطائرة", D, "أقسام جسم مركبة من نوع Barrel وتجميع نهائي في Everett", 18),
 (2005, "787-8", "787", "00", "عام", E, "تغيير الاسم من 7E7 إلى 787 Dreamliner (28 يناير 2005)", 18),
 (2005, "787-8", "787", "53", "جسم الطائرة", E, "خروج أول قسم من هيكل الجسم المصنوع من المواد المركبة (يناير 2005)", 18),
 (2005, "787-8", "787", "00", "عام", E, "تثبيت التصميم الخارجي النهائي (26 أبريل 2005)", 18),
 (2005, "777-200LR", "777", "00", "عام", E, "أول تحليق تجريبي (8 مارس 2005) بعد الطرح في فبراير 2005", 17),
 (2005, "747-8F", "747-8", "00", "عام", E, "الإطلاق الرسمي لبرنامج 747-8 (14 نوفمبر 2005)", 31),
 (2006, ALL, "737NG", "57", "الجناح", D, "Winglets في بعض الطائرات (خصوصاً 737-800) لتقليل مقاومة الهواء", 21),
 (2006, ALL, "737NG", "53", "جسم الطائرة", D, "هيكل من سبائك الألومنيوم 2024-T3 وT6-7075 مع استخدام محدود جداً للمواد المركبة", 21),
 (2006, "737-800", "737NG", "50", "عنابر الشحن", D, "سعة الشحن السفلية ≈44.6 م³", 21),
 (2006, "747-400", "747-400", "53", "جسم الطائرة", D, "هيكل ألمنيوم في معظمه مع تيتانيوم في مناطق الإجهادات العالية", 22),
 (2006, "747-400", "747-400", "32", "معدات الهبوط", D, "استخدام التيتانيوم في بعض تركيبات المحركات وعتاد الهبوط", 22),
 (2006, "777-200LR", "777", "28", "الوقود", D, "إمكانية تركيب خزانات وقود إضافية في الجزء الخلفي من عنبر الشحن", 24),
 (2006, "777-200LR", "777", "32", "معدات الهبوط", D, "تعزيزات في عتاد الهبوط لاستيعاب الأوزان الأعلى", 24),
 (2006, ALL, "777", "27", "أسطح التحكم", D, "أول عائلة تجارية للشركة بنظام Fly-by-Wire على نطاق كامل مع أنظمة احتياطية للتحكم", 24),
 (2006, ALL, "777", "55", "الذيل الأفقي", D, "الذيل الأفقي مصنوع من ألياف الكربون المركّب", 24),
 (2006, "787-8", "787", "51", "الهيكل والمواد", D, "مواد مركبة ≈50% (ألياف الكربون) مع سبائك ألمنيوم-ليثيوم وتيتانيوم في المناطق عالية الإجهاد", 25),
 (2006, "787-8", "787", "36", "الهواء المضغوط", D, "تقليل الاعتماد على Bleed Air والأنظمة الهيدروليكية والهوائية التقليدية", 25),
 (2006, "787-8", "787", "53", "جسم الطائرة", D, "جسم من أقسام كبيرة مركبة بدلاً من عدد كبير من الألواح المعدنية", 25),
 (2006, "717-200", "717", "00", "عام", E, "انتهاء دورة إنتاج 717", 12),
 (2006, "777-200LR", "777", "00", "عام", E, "دخول الخدمة التجارية لدى الخطوط الباكستانية PIA (26 فبراير 2006)", 20),
 (2006, "787-8", "787", "51", "الهيكل والمواد", E, "اتفاقية Toray لتوريد ألياف الكربون (≈6 مليارات دولار) — 26 أبريل 2006", 25),
 (2006, "787-8", "787", "57", "الأجنحة", E, "بدء تجميع صندوق الجناح المركزي في Fuji Heavy Industries (30 يونيو 2006)", 25),
 (2006, "787-8", "787", "00", "عام", E, "عملية Virtual Rollout (6 ديسمبر 2006)", 25),
 (2006, "787-8", "787", "05", "الدعم والصيانة", E, "إطلاق برنامج GoldCare للصيانة والدعم", 25),
 (2006, "747-8F", "747-8", "00", "عام", E, "تثبيت تهيئة نسخة الشحن (أكتوبر 2006)", 31),
 (2007, "737-900ER", "737NG", "00", "عام", E, "دخول الخدمة التجارية (أبريل 2007)", 41),
 (2007, "787-8", "787", "53", "جسم الطائرة", I, "فجوة محاذاة ≈0.3 بوصة بين بعض أقسام الجسم أثناء التجميع (يونيو 2007)", 35),
 (2007, "787-8", "787", "00", "عام", E, "حفل الطرح (8 يوليو 2007) أمام ≈15,000 شخص؛ الطائرة المعروضة هيكل استعراضي غير قابل للطيران", 35),
 (2007, "787-8", "787", "51", "المثبتات", L, "أول تأخير رسمي (5 سبتمبر 2007): نقص المثبتات (Fasteners) وبرمجيات التحكم بالطيران", 35),
 (2007, "787-8", "787", "00", "عام", L, "تأخير إضافي (10 أكتوبر 2007): الطيران التجريبي ≈3 أشهر والتسليم ≈6 أشهر؛ الطلبات ≈706", 35),
 (2008, "737-900ER", "737NG", "52", "الأبواب", D, "رفع السعة والمدى عبر بابي طوارئ إضافيين", 41),
 (2008, "737-900ER", "737NG", "28", "الوقود", D, "خزانات وقود مساعدة اختيارية (المدى ≈5,925 كم)", 41),
 (2008, "737-900ER", "737NG", "53", "جسم الطائرة", D, "تعزيزات هيكلية", 41),
 (2008, "767-300F", "767", "52", "الأبواب", D, "باب علوي رئيسي كبير", 43),
 (2008, "767-300F", "767", "50", "أرضية الشحن", D, "أرضية عنبر معززة وتجهيزات تحميل وتفريغ", 43),
 (2008, "767-300F", "767", "21", "التحكم الحراري", D, "تحكم حراري للبضائع القابلة للتلف", 43),
 (2008, "787-8", "787", "24", "القدرة الكهربائية", D, "محركات GEnx أو Trent 1000 وFly-by-Wire واعتماد موسع على الأنظمة الكهربائية", 46),
 (2008, "787-8", "787", "00", "عام", L, "تأخير ≈3 أشهر (يناير 2008)", 54),
 (2008, "787-8", "787", "00", "عام", L, "تأخير ≈6 أشهر (أبريل 2008)", 54),
 (2008, "747-8F", "747-8", "00", "عام", E, "بدء إنتاج أول طائرة شحن في إفريت (أغسطس 2008)", 42),
 (2008, "787-8", "787", "00", "عام", L, "إضراب عمالي (7 سبتمبر–1 نوفمبر 2008) بمشاركة ≈27,000 عامل", 45),
 (2008, "747-8F", "747-8", "00", "عام", L, "إعلان رسمي بتأخير البرنامج (14 نوفمبر 2008)", 42),
 (2008, "787-8", "787", "00", "عام", L, "تأجيل رسمي لأول تحليق إلى الربع الثاني 2009 (11 ديسمبر 2008)", 45),
 (2009, "777F", "777", "52", "الأبواب", D, "باب شحن جانبي رئيسي", 53),
 (2009, "777F", "777", "56", "النوافذ", D, "إلغاء نوافذ المقصورة وتجهيزها كعنبر شحن", 53),
 (2009, "777F", "777", "50", "أرضية الشحن", D, "أرضية معززة وعنبر شحن لتحمل الأحمال المرتفعة", 53),
 (2009, "777F", "777", "72", "المحركات", D, "GE90-110B1/GE90-115B حصرياً بدفع حتى ≈115,300 رطل", 53),
 (2009, "787-8", "787", "36", "الهواء المضغوط", D, "تقليل الاعتماد على Bleed Air المسحوب من المحركات", 55),
 (2009, "787-8", "787", "31", "قمرة القيادة", D, "قمرة رقمية متقدمة وشاشات عرض كبيرة ونظام إدارة طيران مدمج", 55),
 (2009, "787-8", "787", "27", "أسطح التحكم", D, "نظام تحكم طيران Fly-by-Wire", 55),
 (2009, "787-8", "787", "53", "جسم الطائرة", D, "جسم من هيكل برميلي متكامل بدلاً من تجميع ألواح ألمنيوم", 55),
 (2009, "777F", "777", "00", "عام", E, "شهادة صلاحية FAA/EASA (6 فبراير 2009) ثم تسليم أول طائرة إلى Air France Cargo (19 فبراير)", 53),
 (2009, "787-8", "787", "57", "الأجنحة", I, "مشكلة وصلة الجناح بالجسم (Side-of-Body Join) وإضافة تعزيزات معدنية (يونيو 2009)", 54),
 (2009, "747-8F", "747-8", "00", "عام", L, "تأخير إضافي: أول تحليق إلى الربع الأول 2010", 51),
 (2009, "787-8", "787", "00", "عام", E, "أول تحليق من Paine Field (15 ديسمبر 2009)", 54, "ZA001"),
 (2010, "747-8F", "747-8", "72", "المحركات", D, "4 × GEnx-2B67 بدفع ≈66,500 رطل لكل محرك", 60),
 (2010, "787-8", "787", "24", "القدرة الكهربائية", D, "مفهوم More-Electric Aircraft يتطلب حماية من الأعطال وإدارة طاقة واستمرارية أثناء الطوارئ", 63),
 (2010, "747-8F", "747-8", "00", "عام", E, "أول تحليق (8 فبراير 2010) — 3 ساعات و39 دقيقة", 60, "N747EX"),
 (2010, "787-8", "787", "72", "المحركات", I, "فشل محرك Rolls-Royce Trent 1000 أثناء اختبار أرضي (27 أغسطس 2010)", 63),
 (2010, "787-8", "787", "24", "القدرة الكهربائية", I, "حريق كهربائي أثناء رحلة اختبار → هبوط اضطراري وتعليق الاختبارات (9 نوفمبر 2010)", 63, "ZA002"),
 (2010, "787-8", "787", "24", "القدرة الكهربائية", E, "استئناف اختبارات الطيران تدريجياً بعد تحديث برمجيات توزيع الطاقة (25 ديسمبر 2010)", 63, "ZA004"),
]
REC_COLS = ["rec_id", "year", "model", "program", "aircraft", "ata", "subsystem", "category", "status", "note", "source", "updated"]


def build_records() -> pd.DataFrame:
    rows = []
    for i, rec in enumerate(RECORDS, 1):
        y, m, p, a, s, c, n, pg = rec[:8]
        rows.append(dict(rec_id=f"REC-{i:03d}", year=int(y), model=m, program=p, aircraft=(rec[8] if len(rec) > 8 else "—"),
                         ata=a, subsystem=s, category=c, status=STATUS_BY_CAT[c], note=n, source=f"ص {pg}", updated="—"))
    return pd.DataFrame(rows, columns=REC_COLS)


if "records" not in st.session_state:
    st.session_state["records"] = build_records()
records: pd.DataFrame = st.session_state["records"]

def ata_label(code: str) -> str:
    return f"ATA {code} – {ATA[code][0]}" if code in ATA else f"ATA {code}"


def show_df(df: pd.DataFrame, **kw) -> None:
    if _NEW_API:
        st.dataframe(df, width="stretch", hide_index=True, **kw)
    else:
        st.dataframe(df, use_container_width=True, hide_index=True, **kw)


def show_plot(fig: go.Figure) -> None:
    fig.update_layout(template="plotly_white", font=dict(family="Tahoma, Arial", size=13),
                      margin=dict(l=10, r=10, t=50, b=10), title_x=1, title_xanchor="right")
    if _NEW_API:
        st.plotly_chart(fig, width="stretch")
    else:
        st.plotly_chart(fig, use_container_width=True)


def display_records(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ata"] = out["ata"].map(ata_label)
    out = out[["rec_id", "aircraft", "model", "year", "subsystem", "ata", "category", "status", "note", "source", "updated"]]
    out.columns = ["رقم السجل", "معرّف الطائرة", "الطراز", "السنة", "النظام الفرعي", "فصل ATA", "نوع السجل", "الحالة",
                   "الملاحظة الفنية", "المصدر", "آخر تحديث"]
    return out


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")


# ───────────────────────── الشريط الجانبي ─────────────────────────
PAGES = ["📊 لوحة المؤشرات", "🔎 البحث والمرجع في الأسطول", "📚 دليل فصول ATA", "✏️ تحديث أو إضافة سجل"]
st.sidebar.title("✈️ مرجع بوينغ")
st.sidebar.caption("السجلات الهندسية 2004–2010")
page = st.sidebar.radio("القائمة", PAGES)
st.sidebar.divider()
st.sidebar.subheader("المرشحات العامة")
sel_models = st.sidebar.multiselect("طراز الطائرة", MODELS["model"].tolist(), placeholder="كل الطرازات")
year_rng = st.sidebar.slider("السنة", 2004, 2010, (2004, 2010))
sel_ata = st.sidebar.multiselect("فصل ATA", sorted(records["ata"].unique()), format_func=ata_label, placeholder="كل الفصول")
with st.sidebar.expander("ℹ️ عن البيانات"):
    st.markdown(
        "- المصدر: ملف **Boeing_2004_2010.pdf**، وهو موسوم داخلياً بأنه *سجل خيالي*.\n"
        "- الملف لا يتضمن أرقام تسجيل ولا سجلات صيانة؛ **معرّف الطائرة** يظهر فقط حيث ذُكر في النص (ZA001…).\n"
        "- **فصل ATA** و**النظام الفرعي** و**الحالة** تصنيف تحليلي مشتق من نص كل ملاحظة.\n"
        "- التعديلات من صفحة «تحديث أو إضافة سجل» محاكاة تعيش في الجلسة الحالية فقط."
    )


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    out = df[df["year"].between(*year_rng)]
    if sel_models:
        progs = set(MODELS.loc[MODELS["model"].isin(sel_models), "program"])
        out = out[out["model"].isin(sel_models) | ((out["model"] == ALL) & out["program"].isin(progs))]
    if sel_ata:
        out = out[out["ata"].isin(sel_ata)]
    return out


def filter_models() -> pd.DataFrame:
    out = MODELS[MODELS["first_year"] <= year_rng[1]]
    if sel_models:
        out = out[out["model"].isin(sel_models)]
    return out


rec_f = apply_filters(records)
mod_f = filter_models()

# ───────────────────────── 1) لوحة المؤشرات ─────────────────────────
def page_dashboard() -> None:
    st.title("📊 لوحة المؤشرات ومعرض الأسطول")

    # عرض الصور الخمس في المربعات العلوية فقط وبشكل مرتب
    st.subheader("📸 لقطات أسطول بوينغ (2004–2010)")

    current_dir = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else "."

    images_data = [
        ("image", "بوينغ 787 دريملاينر (ANA)"),
        ("image_2", "بوينغ 747-8F (الإنتاج)"),
        ("image_3", "بوينغ 737 (Qantas)"),
        ("image_4", "بوينغ 777 (China Eastern)"),
        ("image_5", "بوينغ 747 (Lufthansa)")
    ]

    img_cols = st.columns(len(images_data))

    for col, (img_name, caption_text) in zip(img_cols, images_data):
        with col:
            found = False
            for ext in [".jpeg", ".jpg", ".png", ".JPEG", ".JPG", ".PNG"]:
                p = os.path.join(current_dir, img_name + ext)
                if os.path.exists(p):
                    try:
                        st.image(p, caption=caption_text, use_container_width=True)
                        found = True
                        break
                    except Exception:
                        pass
            if not found:
                st.warning("الصورة غير متوفرة")

    st.divider()

    if rec_f.empty:
        st.info("لا توجد سجلات تطابق المرشحات الحالية.")
    else:
        left, right = st.columns(2)
        with left:
            cnt = rec_f.groupby("ata").size().reset_index(name="n")
            cnt["label"] = cnt["ata"].map(ata_label)
            cnt = cnt.sort_values("n", ascending=False).head(12)
            fig = px.bar(cnt, x="n", y="label", orientation="h", title="الفصول الأكثر ورودًا في السجلات",
                         labels={"n": "عدد السجلات", "label": "فصل ATA"}, color_discrete_sequence=["#1F4E79"])
            fig.update_yaxes(categoryorder="total ascending")
            show_plot(fig)
        with right:
            yc = rec_f.assign(year=rec_f["year"].astype(str)).groupby(["year", "category"]).size().reset_index(name="n")
            fig = px.bar(yc, x="year", y="n", color="category", title="التوزيع حسب السنوات ونوع السجل",
                         labels={"year": "السنة", "n": "عدد السجلات", "category": "نوع السجل"},
                         category_orders={"year": [str(y) for y in YEARS]}, color_discrete_sequence=px.colors.qualitative.Safe)
            show_plot(fig)

    left, right = st.columns(2)
    with left:
        sc = mod_f.dropna(subset=["range_km", "mtow_kg"])
        if sc.empty:
            st.info("لا توجد طرازات بمدى وأقصى وزن إقلاع ضمن المرشحات.")
        else:
            fig = px.scatter(sc, x="range_km", y="mtow_kg", color="program", text="model", hover_name="model",
                             title="المدى مقابل أقصى وزن إقلاع (أحدث قيم لكل طراز)",
                             labels={"range_km": "المدى (كم)", "mtow_kg": "MTOW (كغم)", "program": "البرنامج"})
            fig.update_traces(textposition="top center", marker=dict(size=11))
            show_plot(fig)
    with right:
        ps = PROG_STATUS[PROG_STATUS["year"].between(*year_rng)]
        if sel_models:
            ps = ps[ps["program"].isin(set(MODELS.loc[MODELS["model"].isin(sel_models), "program"]))]
        if ps.empty:
            st.info("لا توجد حالات برامج ضمن المرشحات.")
        else:
            ps = ps.assign(code=ps["status"].map(STATUS_CODE), ar=ps["status"].map(STATUS_AR))
            z = ps.pivot(index="program", columns="year", values="code")
            t = ps.pivot(index="program", columns="year", values="ar").fillna("")
            scale = [[0, "#8E6C8A"], [.25, "#8E6C8A"], [.25, "#D98E04"], [.5, "#D98E04"],
                     [.5, "#2A7F62"], [.75, "#2A7F62"], [.75, "#7D828A"], [1, "#7D828A"]]
            fig = go.Figure(go.Heatmap(z=z.values, x=[str(c) for c in z.columns], y=z.index.tolist(), text=t.values,
                                       texttemplate="%{text}", colorscale=scale, zmin=-0.5, zmax=3.5, showscale=False,
                                       xgap=2, ygap=2, textfont=dict(color="white", size=11), hoverongaps=False))
            fig.update_layout(title="حالة البرامج عبر السنوات")
            fig.update_xaxes(type="category")
            show_plot(fig)


# ───────────────────────── 2) البحث والمرجع في الأسطول ─────────────────────────
def page_fleet() -> None:
    st.title("🔎 البحث والمرجع في الأسطول")
    tab1, tab2 = st.tabs(["السجلات الفنية", "مواصفات الطرازات"])
    with tab1:
        c1, c2, c3 = st.columns([2, 1, 1])
        q = c1.text_input("بحث نصي", placeholder="اكتب كلمة: محرك، Fly-by-Wire، ZA002، ATA 72 ...")
        cats = c2.multiselect("نوع السجل", CATS)
        stats = c3.multiselect("الحالة", STATUS_OPTIONS)
        view = rec_f
        if cats:
            view = view[view["category"].isin(cats)]
        if stats:
            view = view[view["status"].isin(stats)]
        if q.strip():
            hay = view[["rec_id", "aircraft", "model", "program", "subsystem", "category", "status", "note"]].astype(str)
            hay = hay.assign(ata=view["ata"].map(ata_label))
            mask = hay.apply(lambda s: s.str.contains(q.strip(), case=False, regex=False)).any(axis=1)
            view = view[mask]
        st.write(f"**{len(view)}** سجل من أصل {len(records)}")
        shown = display_records(view.sort_values(["year", "rec_id"]))
        show_df(shown)
        st.download_button("⬇️ تنزيل النتائج (CSV)", csv_bytes(shown), "boeing_records.csv", "text/csv")
        if len(view):
            st.subheader("تفاصيل سجل")
            rid = st.selectbox("اختر سجلاً", view["rec_id"].tolist(),
                               format_func=lambda r: f"{r} — {view.loc[view['rec_id'] == r, 'note'].iloc[0][:60]}")
            r = view[view["rec_id"] == rid].iloc[0]
            with st.container(border=True):
                a, b, c = st.columns(3)
                a.markdown(f"**الطراز:** {r['model']}  \n**البرنامج:** {r['program']}")
                b.markdown(f"**السنة:** {r['year']}  \n**معرّف الطائرة:** {r['aircraft']}")
                c.markdown(f"**{ata_label(r['ata'])}**  \n**النظام الفرعي:** {r['subsystem']}")
                st.markdown(f"**نوع السجل / الحالة:** {r['category']} / {r['status']}")
                st.markdown(f"**الملاحظة الفنية:** {r['note']}")
                st.caption(f"المصدر: {r['source']} — آخر تحديث: {r['updated']}")
    with tab2:
        m = mod_f.rename(columns={"model": "الطراز", "program": "البرنامج", "family": "العائلة", "body": "البدن", "kind": "النوع",
                                  "first_year": "أول تقرير", "length_m": "الطول (م)", "wingspan_m": "الباع (م)",
                                  "oew_kg": "الوزن الفارغ (كغم)", "mtow_kg": "MTOW (كغم)", "payload_kg": "الحمولة (كغم)",
                                  "range_km": "المدى (كم)", "mach": "Mach"})
        st.caption("أحدث قيمة غير فارغة لكل خاصية عبر تقارير 2004–2010؛ الفراغ يعني أن القيمة غير مذكورة في الملف.")
        show_df(m)
        st.download_button("⬇️ تنزيل المواصفات (CSV)", csv_bytes(m), "boeing_models.csv", "text/csv")


# ───────────────────────── 3) دليل فصول ATA ─────────────────────────
def page_ata() -> None:
    st.title("📚 دليل فصول ATA")
    q = st.text_input("ابحث عن فصل", placeholder="مثال: 27 أو الهبوط أو وقود").strip().lower()
    tabs = st.tabs(list(ATA_GROUPS))
    for tab, (gname, codes) in zip(tabs, ATA_GROUPS.items()):
        with tab:
            shown = 0
            for code in codes:
                name, desc = ATA[code]
                if q and q not in f"{code} {name} {desc}".lower():
                    continue
                shown += 1
                sub = rec_f[rec_f["ata"] == code]
                with st.expander(f"ATA {code} — {name}   ({len(sub)} سجل)"):
                    st.write(desc)
                    if sub.empty:
                        st.caption("لا توجد سجلات لهذا الفصل ضمن المرشحات الحالية.")
                    else:
                        subs = ", ".join(sorted(sub["subsystem"].unique()))
                        st.markdown(f"**الأنظمة الفرعية الواردة:** {subs}")
                        show_df(display_records(sub.sort_values("year")).drop(columns=["فصل ATA"]))
            if shown == 0:
                st.info("لا توجد فصول مطابقة للبحث في هذه المجموعة.")


# ───────────────────────── 4) تحديث أو إضافة سجل ─────────────────────────
def next_id(df: pd.DataFrame) -> str:
    nums = pd.to_numeric(df["rec_id"].str.extract(r"(\d+)$")[0], errors="coerce").dropna()
    return f"REC-{int(nums.max()) + 1 if len(nums) else 1:03d}"


def page_edit() -> None:
    st.title("✏️ تحديث أو إضافة سجل")
    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))
    st.info("نموذج محاكى: التغييرات تُحفظ في جلسة المتصفح الحالية فقط ولا تُكتب في أي ملف. يمكنك تنزيل السجلات المحدّثة بصيغة CSV.")
    mode = st.radio("العملية", ["إضافة ملاحظة فنية جديدة", "تحديث سجل قائم"], horizontal=True)
    ata_codes = sorted(ATA)

    if mode == "إضافة ملاحظة فنية جديدة":
        with st.form("add_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            model = c1.selectbox("طراز الطائرة", MODELS["model"].tolist())
            year = c2.selectbox("السنة", YEARS)
            ata = c3.selectbox("فصل ATA", ata_codes, format_func=ata_label, index=ata_codes.index("27"))
            c4, c5, c6 = st.columns(3)
            subsystem = c4.text_input("النظام الفرعي", placeholder="مثال: المصاعد، العجلة الأمامية")
            category = c5.selectbox("نوع السجل", CATS, index=CATS.index("ملاحظة صيانة"))
            status = c6.selectbox("الحالة", STATUS_OPTIONS, index=STATUS_OPTIONS.index("قيد المتابعة"))
            aircraft = st.text_input("معرّف الطائرة / رقم التسجيل (اختياري)", placeholder="مثال: ZA001")
            note = st.text_area("الملاحظة الفنية", placeholder="صف الملاحظة أو الإجراء الفني (10 أحرف على الأقل)...", height=120)
            if st.form_submit_button("➕ إضافة السجل", type="primary"):
                if len(note.strip()) < 10 or not subsystem.strip():
                    st.error("يرجى إدخال النظام الفرعي وملاحظة فنية لا تقل عن 10 أحرف.")
                else:
                    prog = MODELS.loc[MODELS["model"] == model, "program"].iloc[0]
                    new = dict(rec_id=next_id(records), year=int(year), model=model, program=prog,
                               aircraft=aircraft.strip() or "—", ata=ata, subsystem=subsystem.strip(), category=category,
                               status=status, note=note.strip(), source="إدخال يدوي (محاكاة)",
                               updated=datetime.now().strftime("%Y-%m-%d %H:%M"))
                    st.session_state["records"] = pd.concat([records, pd.DataFrame([new])], ignore_index=True)
                    st.session_state["flash"] = f"تمت إضافة السجل {new['rec_id']} بنجاح."
                    st.rerun()
    else:
        if records.empty:
            st.warning("لا توجد سجلات للتحديث.")
        else:
            rid = st.selectbox("السجل المراد تحديثه", records["rec_id"].tolist(),
                               format_func=lambda r: f"{r} | {records.loc[records['rec_id'] == r, 'year'].iloc[0]} | "
                                                     f"{records.loc[records['rec_id'] == r, 'model'].iloc[0]} | "
                                                     f"{records.loc[records['rec_id'] == r, 'note'].iloc[0][:45]}")
            idx = records.index[records["rec_id"] == rid][0]
            cur = records.loc[idx]
            with st.form(f"upd_form_{rid}"):
                st.caption(f"الطراز: {cur['model']} — السنة: {cur['year']} — المصدر: {cur['source']}")
                c1, c2, c3 = st.columns(3)
                ata = c1.selectbox("فصل ATA", ata_codes, format_func=ata_label,
                                   index=ata_codes.index(cur["ata"]) if cur["ata"] in ata_codes else 0)
                subsystem = c2.text_input("النظام الفرعي", value=cur["subsystem"])
                status = c3.selectbox("الحالة", STATUS_OPTIONS,
                                      index=STATUS_OPTIONS.index(cur["status"]) if cur["status"] in STATUS_OPTIONS else 0)
                note = st.text_area("الملاحظة الفنية", value=cur["note"], height=120)
                if st.form_submit_button("💾 حفظ التحديث", type="primary"):
                    if len(note.strip()) < 10 or not subsystem.strip():
                        st.error("يرجى إدخال النظام الفرعي وملاحظة فنية لا تقل عن 10 أحرف.")
                    else:
                        df = records.copy()
                        df.loc[idx, ["ata", "subsystem", "status", "note", "updated"]] = [
                            ata, subsystem.strip(), status, note.strip(), datetime.now().strftime("%Y-%m-%d %H:%M")]
                        st.session_state["records"] = df
                        st.session_state["flash"] = f"تم تحديث السجل {rid}."
                        st.rerun()

    st.divider()
    c1, c2 = st.columns([3, 1])
    c1.subheader("آخر السجلات المُعدَّلة أو المضافة")
    if c2.button("↩️ إعادة ضبط البيانات الأصلية"):
        st.session_state["records"] = build_records()
        st.rerun()
    touched = records[records["updated"] != "—"]
    if touched.empty:
        st.caption("لم تُجرَ أي تعديلات بعد.")
    else:
        show_df(display_records(touched))
    st.download_button("⬇️ تنزيل كل السجلات (CSV)", csv_bytes(display_records(records)), "boeing_records_all.csv", "text/csv")


# ───────────────────────── التوجيه ─────────────────────────
if page == PAGES[0]:
    page_dashboard()
elif page == PAGES[1]:
    page_fleet()
elif page == PAGES[2]:
    page_ata()
else:
    page_edit()