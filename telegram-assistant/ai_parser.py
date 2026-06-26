import json
import re
from datetime import datetime
import pytz
import httpx


async def parse_task_with_ai(text: str, api_key: str, timezone: str) -> dict:
    """
    ورودی: متن فارسی از کاربر
    خروجی: لیست تسک‌های استخراج‌شده با زمان و تکرار
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    now_str = now.strftime("%Y-%m-%d %H:%M %A")
    weekday_fa = {
        "Monday": "دوشنبه", "Tuesday": "سه‌شنبه", "Wednesday": "چهارشنبه",
        "Thursday": "پنج‌شنبه", "Friday": "جمعه", "Saturday": "شنبه", "Sunday": "یکشنبه"
    }
    weekday = weekday_fa.get(now.strftime("%A"), now.strftime("%A"))

    system_prompt = f"""تو یک پارسر هوشمند تسک هستی. 
الان: {now_str} ({weekday}) — منطقه زمانی: {timezone}

وظیفه‌ات اینه که از پیام فارسی کاربر، تسک‌ها رو استخراج کنی.

قوانین:
- «فردا» یعنی {(now.date().__class__.__name__)} یعنی یک روز بعد از امروز
- ساعت‌های فارسی مثل «ده» یعنی ۱۰:۰۰، «نه و نیم» یعنی ۰۹:۳۰
- اگر AM/PM مشخص نشده و ساعت بین ۱-۸ بود، احتمالاً PM (عصر) است
- «هر دوشنبه» یا «هر روز» نشون‌دهنده recurring است
- اگه زمانی ذکر نشده، due_datetime رو null بذار

فرمت خروجی — فقط JSON بدون هیچ توضیح اضافه:
{{
  "tasks": [
    {{
      "title": "عنوان تسک به فارسی",
      "due_datetime": "2025-01-15T10:00:00+03:30",
      "is_recurring": false,
      "recurrence_rule": null,
      "reminder_minutes": 15
    }}
  ]
}}

اگه تسکی تشخیص ندادی: {{"tasks": []}}
"""

    payload = {
        "model": "claude-sonnet-4-6",
        "max_tokens": 1000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": text}]
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload
            )
            resp.raise_for_status()
            data = resp.json()

        raw = data["content"][0]["text"].strip()
        # Strip markdown fences if present
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)

    except Exception as e:
        print(f"AI parse error: {e}")
        return {"tasks": []}
