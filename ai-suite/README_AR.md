# حزمة Byblos AI

هذه الحزمة تحتوي على مشروعين مترابطين:

- `android-app/`: تطبيق Android يعمل من Android 6 فما فوق، مبني بـJetpack Compose.
- `backend/`: خادم Node.js يحتفظ بمفتاح OpenAI خارج ملف APK ويبث الإجابة تدريجيًا إلى التطبيق.

## حدود الأمان

لا يحتوي تطبيق Android على `OPENAI_API_KEY`. المفتاح موجود في بيئة الخادم فقط. المتغير `BACKEND_API_TOKEN` بوابة اختبار خاصة لا أكثر؛ يمكن استخراج أي قيمة ثابتة من APK، ولذلك لا يصلح هذا الرمز كمصادقة لمستخدمين حقيقيين.

قبل النشر العام يجب إضافة تسجيل دخول حقيقي، والتحقق من رمز المستخدم على الخادم، وتحديد حصة استخدام لكل حساب.

## التشغيل المحلي

### 1. تشغيل الخادم

```bash
cd backend
cp .env.example .env
npm install
npm test
npm start
```

عدّل `.env` وضع مفتاح OpenAI في `OPENAI_API_KEY`. الإعداد الافتراضي للنموذج هو `gpt-5-mini` ويمكن تغييره إلى نموذج متاح في مشروعك. لا ترفع ملف `.env` إلى Git.

الخادم يعمل افتراضيًا على المنفذ `3000`.

### 2. تشغيل Android

1. افتح مجلد `android-app/` في Android Studio.
2. استخدم JDK 17 وثبّت Android SDK 37.
3. شغّل Backend أولًا.
4. شغّل نسخة Debug على المحاكي.

نسخة Debug تتصل تلقائيًا بالعنوان:

```text
http://10.0.2.2:3000/
```

على هاتف حقيقي، استبدل عنوان Debug بعنوان الحاسوب داخل الشبكة المحلية أو استخدم نطاق HTTPS تجريبيًا.

## الاختبارات والبناء

```bash
cd android-app
./gradlew clean testDebugUnitTest
./gradlew connectedDebugAndroidTest
```

إنشاء Android App Bundle للإصدار:

```bash
./gradlew bundleRelease \
  -PBACKEND_BASE_URL=https://api.example.com/ \
  -PBACKEND_API_TOKEN=
```

لا تستخدم `BACKEND_API_TOKEN` الثابت في إصدار عام.

## الموجود داخل الحزمة

- واجهة Jetpack Compose عربية.
- ViewModel و`StateFlow`.
- قاعدة Room وحفظ المحادثات محليًا.
- Migration حقيقي من الإصدار 1 إلى 2.
- بث SSE باستخدام OkHttp.
- حد أقصى لطول الرسائل وعدد رسائل السياق.
- HTTPS فقط في إصدار Release.
- R8 وتصغير الموارد.
- Rate limiting والتحقق من المدخلات وحد لحجم الطلبات على الخادم.
- اختبارات Unit وCompose وRoom وBackend.
- Dockerfile للخادم.

## المتبقي قبل Google Play

- مصادقة مستخدمين حقيقية وحصص استخدام.
- نطاق إنتاجي وTLS ومراقبة وسجلات وأخذ نسخ احتياطية.
- سياسة خصوصية وشروط استخدام ونموذج Data Safety وآلية حذف الحساب والبيانات.
- Play App Signing ومفتاح Upload ومواد صفحة المتجر.
- اختبار فعلي على API 23 حتى API 37، واختبارات Root/Non-Root عند التعامل مع بيانات حساسة.
