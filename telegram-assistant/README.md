# 🤖 ربات دستیار هوشمند تلگرام

ربات منشی شخصی تلگرام با قابلیت ثبت تسک از متن فارسی طبیعی، یادآوری خودکار و خلاصه روزانه.

---

## ✨ قابلیت‌ها

- 📝 **ثبت تسک از متن طبیعی فارسی** — بدون فرم، فقط بنویسید
- ⏰ **یادآوری X دقیقه قبل** از هر تسک (قابل تنظیم برای هر کاربر)
- 🌅 **خلاصه روزانه** هر صبح ساعت ۸
- 🔁 **تسک‌های تکراری** — «هر دوشنبه»، «هر روز»
- ✅ **مدیریت تسک‌ها** — انجام‌شده، حذف، لیست

---

## 🚀 راه‌اندازی

### ۱. ساخت ربات تلگرام

۱. به [@BotFather](https://t.me/BotFather) برید
۲. `/newbot` بزنید و اسم ربات بدید
۳. توکن رو کپی کنید

### ۲. دریافت Anthropic API Key

۱. به [console.anthropic.com](https://console.anthropic.com) برید
۲. یک API Key بسازید

### ۳. Deploy روی Railway (رایگان)

```bash
# ۱. Fork یا clone این repo
git clone <your-repo-url>
cd telegram-assistant

# ۲. Railway CLI نصب کنید
npm install -g @railway/cli

# ۳. لاگین و deploy
railway login
railway init
railway up
```

در داشبورد Railway، متغیرهای محیطی رو تنظیم کنید:

| متغیر | مقدار |
|-------|-------|
| `BOT_TOKEN` | توکن ربات از BotFather |
| `ANTHROPIC_API_KEY` | کلید API آنتروپیک |
| `TIMEZONE` | `Asia/Tehran` |
| `REMINDER_MINUTES` | `15` |
| `DAILY_SUMMARY_HOUR` | `8` |

### ۴. Deploy روی Render (جایگزین)

۱. یک حساب در [render.com](https://render.com) بسازید
۲. New → Background Worker انتخاب کنید
۳. Repo رو connect کنید
۴. Build Command: `pip install -r requirements.txt`
۵. Start Command: `python bot.py`
۶. متغیرهای محیطی رو از جدول بالا اضافه کنید

---

## 💬 نمونه پیام‌ها

```
فردا ساعت ۱۰ جلسه با تیم مارکتینگ دارم
امشب ساعت ۸ باید گزارش ماهانه بنویسم
هر دوشنبه ساعت ۹ تیم‌میتینگ داریم
یک ساعت دیگه با مشتری تماس دارم
```

## 📋 دستورات

| دستور | توضیح |
|-------|-------|
| `/tasks` | برنامه امروز |
| `/all` | همه تسک‌های فعال |
| `/done` | علامت‌گذاری انجام‌شده |
| `/delete` | حذف تسک |
| `/settings` | تنظیم زمان یادآوری |
| `/help` | راهنما |

---

## 🗂 ساختار پروژه

```
telegram-assistant/
├── bot.py          # منطق اصلی ربات
├── database.py     # پایگاه داده SQLite
├── ai_parser.py    # پردازش متن با Claude AI
├── requirements.txt
├── Procfile        # برای Railway/Render
└── .env.example    # نمونه متغیرهای محیطی
```
