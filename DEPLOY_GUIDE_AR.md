# دليل رفع الأداة على GitHub ونشرها على Streamlit Cloud

## 1) جهز الملفات
لازم يكون عندك الملفات التالية في فولدر واحد:
- `app.py`
- `requirements.txt`
- `README.md`

## 2) اعمل حسابات
تحتاج:
- حساب GitHub
- حساب Streamlit Community Cloud

## 3) ارفع المشروع على GitHub
### الطريقة الأسهل من المتصفح
1. ادخل على [GitHub](https://github.com)
2. اضغط **New repository**
3. سمِّ المشروع مثلًا: `competitive-promo-agent`
4. اجعل المشروع **Public** في البداية لتسهيل النشر
5. اضغط **Create repository**
6. داخل الـ repo اضغط **Add file** ثم **Upload files**
7. ارفع الملفات: `app.py`, `requirements.txt`, `README.md`
8. اضغط **Commit changes**

## 4) انشر على Streamlit Cloud
1. ادخل على [Streamlit Community Cloud](https://share.streamlit.io/)
2. سجل الدخول بحساب GitHub
3. اضغط **New app** أو **Create app**
4. اختر الـ repository الذي رفعته
5. اختر الفرع غالبًا `main`
6. في خانة **Main file path** اكتب: `app.py`
7. اضغط **Deploy**

## 5) افتح الأداة
بعد النشر، Streamlit سيعطيك رابط مباشر للأداة.
افتحه من المتصفح وستظهر لك صفحة التطبيق.

## 6) لو حصل خطأ في النشر
راجع الآتي:
- هل `requirements.txt` موجود؟
- هل `app.py` موجود في جذر المشروع؟
- هل اسم الملف في Streamlit مكتوب بالضبط `app.py`؟

## 7) ملاحظات مهمة
- إذا استخدمت Playwright Screenshots قد تحتاج إعدادات إضافية حسب بيئة النشر.
- كبداية، يمكنك نشر الأداة بدون تفعيل screenshots لو ظهرت مشكلة.
- بعد نجاح النشر الأساسي، نكمل تحسينات OCR والـ screenshots.
