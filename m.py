import re
import asyncio
import requests
from telethon import TelegramClient, events

# 🔹 ใส่ API ID และ API HASH
API_ID = 29316101
API_HASH = "81d03af65c3d3a442f38559d3967e28c"
PHONE_NUMBERS = [
    "0951417365", "0959694413", "0829196672", "0659599070"
]
NOTIFY_GROUP_ID = -1002405260670  # ใส่ Group ID ที่ต้องการแจ้งเตือน

# 🔹 บันทึกซองที่เคยใช้ไปแล้ว
used_links = set()

# 🔹 เชื่อมต่อ Telegram
client = TelegramClient("truemoney_bot", API_ID, API_HASH)

# 🔹 ดักจับข้อความที่มีลิงก์ซอง
@client.on(events.NewMessage)
async def handler(event):
    message = event.message.message
    link_pattern = r"https://gift\.truemoney\.com/campaign[^\s]*v=([\w\d]+)"
    match = re.search(link_pattern, message)

    if match:
        angpao_code = match.group(1)

        if angpao_code in used_links:
            print(f"🚫 ซองนี้ถูกใช้ไปแล้ว: {angpao_code}")
            return  # ไม่ให้รับซ้ำ

        used_links.add(angpao_code)
        print(f"🎁 พบซอง: {angpao_code}")

        # 🔹 ลองเติมเงินในทุกเบอร์
        for phone in PHONE_NUMBERS:
            success, amount = claim_angpao(angpao_code, phone)
            if success:
                await notify_success(phone, angpao_code, amount)
            else:
                await notify_fail(phone, angpao_code)

# 🔹 ฟังก์ชันส่งซองไปยัง API
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data.get("status", {}).get("message", "").lower() == "success":
            tickets = data.get("data", {}).get("tickets", [])
            amount_total = sum(float(ticket["amount_baht"]) for ticket in tickets if ticket["mobile"].replace("-", "") == phone)
            return True, amount_total
    except Exception as e:
        print(f"⚠️ เกิดข้อผิดพลาด: {e}")

    return False, 0.00

# 🔹 แจ้งเตือนเมื่อเติมเงินสำเร็จ
async def notify_success(phone, code, amount):
    message = f"✅ เบอร์ {phone} รับเงิน {amount:.2f} บาท จากซอง {code} สำเร็จ!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

# 🔹 แจ้งเตือนเมื่อเติมเงินไม่สำเร็จ
async def notify_fail(phone, code):
    message = f"❌ เบอร์ {phone} รับซอง {code} ไม่สำเร็จ!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

# 🔹 เริ่มรันบอท
async def main():
    print("🚀 กำลังรันบอท...")
    await client.start()
    print("✅ บอทเชื่อมต่อสำเร็จ!")
    await client.run_until_disconnected()

asyncio.run(main())
