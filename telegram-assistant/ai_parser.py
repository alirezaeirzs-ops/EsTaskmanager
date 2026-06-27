import json
import re
from datetime import datetime, timedelta
import pytz
import httpx


async def parse_task_with_ai(text: str, api_key: str, timezone: str) -> dict:
    """
    ورودی: متن فارسی از کاربر
    خروجی: لیست تسک‌های استخراج‌شده با زمان و تکرار
    — از Google Gemini API (رایگان) استفاده می‌کنه
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    today = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M")
    weekday_fa = {
        "Monday": "دوشنبه", "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه",
        "Thursday": "پنج‌شنبه", "Friday": "جمعه", "Saturday": "شنبه", "Sunday": "یکشنبه"
    }
    weekday = weekday_fa.get(now.strftime("%A"), now.strftime("%A"))
    offset = now.strftime("%z")  # e.g. +0330
    offset_str = f"{offset[:3]}:{offset[3:]}"  # +03:30

    prompt = f"""تو یک پارسر هوشمند تسک هستی.
الان: {now_str} ({weekday}) — منطقه زمانی: {timezone} (offset: {offset_str})
امروز: {today}
فردا: {tomorrow}

وظیفه‌ات اینه که از پیام فارسی کاربر، تسک‌ها رو استخراج کنی.

قوانین:
- «فردا» = {tomorrow}
- «امشب» = امروز {today} ولی بعدازظهر/شب
- ساعت فارسی: «ده» = 10:00، «نه و نیم» = 09:30، «هفت و ربع» = 07:15
- اگر ساعت بین ۱ تا ۷ بود و صبح/ظهر ذکر نشده، احتمالاً عصر/شب است (PM)
- «هر دوشنبه»، «هر روز»، «هفتگی» = is_recurring: true
- اگه زمان ذکر نشده، due_datetime را null بگذار
- timezone offset را حتماً در due_datetime بگذار: مثال 2025-01-15T10:00:00+03:30

فقط JSON خالص برگردان، بدون توضیح یا markdown:
{{"tasks": [{{"title": "عنوان تسک", "due_datetime": "ISO8601 با offset یا null", "is_recurring": false, "recurrence_rule": null, "reminder_minutes": 15}}]}}

اگه تسکی نبود: {{"tasks": []}}

پیام کاربر: {text}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1000,
        }
    }

    # Gemini 2.0 Flash — رایگان و سریع
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)

    except Exception as e:
        print(f"Gemini parse error: {e}")
        return {"tasks": []}
