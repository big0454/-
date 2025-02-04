# -*- coding: utf-8 -*-
import asyncio
import re
import json
import requests
from telethon import TelegramClient, events

# 🔹 ตั้งค่า API สำหรับ Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"

# 🔹 เบอร์ที่ใช้รับซอง
phone_numbers = [
    "0951417365",
    "0959694413",
    "0829196672",
    "0659599070"
]

# 🔹 กลุ่มที่ใช้แจ้งเตือน
notify_group_id = -1002405260670

# 🔹 URL API เติมเงินซอง
topup_api_url = "https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{}/{}"

# ✅ สร้าง Client สำหรับ Telegram
client = TelegramClient("my_telegram_session", api_id, api_hash)

# 🔍 ฟังก์ชันดึงโค้ดจากลิงก์ซอง
def extract_angpao_code(text):
    match = re.search(r"https://gift\.truemoney\.com/campaign\?v=([a-zA-Z0-9]+)", text)
    if match:
        return match.group(1)
    return None

# 📥 ดักข้อความที่มีซองและจัดการ
@client.on(events.NewMessage)
async def handler(event):
    message = event.message.message

    # 🔍 ตรวจหาลิงก์ซอง
    angpao_code = extract_angpao_code(message)
    if angpao_code:
        print(f"🔍 พบซอง: {angpao_code}")
        
        success_numbers = []
        failed_numbers = []

        # 🔄 ลองเติมเงินซองให้ทุกเบอร์
        for phone in phone_numbers:
            try:
                url = topup_api_url.format(angpao_code, phone)
                response = requests.get(url)
                data = response.json()

                if data.get("status", {}).get("code") == "SUCCESS":
                    amount = data.get("data", {}).get("voucher", {}).get("amount_baht", "0.00")
                    success_numbers.append((phone, amount))
                    print(f"✅ เบอร์ {phone} รับซองสำเร็จ! ({amount} บาท)")
                else:
                    failed_numbers.append(phone)
                    print(f"❌ เบอร์ {phone} รับซองไม่สำเร็จ")
            
            except Exception as e:
                print(f"⚠️ เกิดข้อผิดพลาดกับเบอร์ {phone}: {str(e)}")
                failed_numbers.append(phone)

        # 📢 แจ้งเตือนในกลุ่ม
        msg = f"🎁 ซอง: `{angpao_code}`\n"
        if success_numbers:
            msg += "✅ สำเร็จ:\n" + "\n".join([f"- {p[0]} ({p[1]} บาท)" for p in success_numbers]) + "\n"
        if failed_numbers:
            msg += "❌ ไม่สำเร็จ:\n" + "\n".join([f"- {p}" for p in failed_numbers]) + "\n"
        
        await client.send_message(notify_group_id, msg)

# 🚀 รันบอท
async def main():
    await client.start()
    print("✅ บอททำงานแล้ว!")
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
