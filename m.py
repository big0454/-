import re
import asyncio
import requests
from telethon import TelegramClient, events

API_ID = 29316101
API_HASH = "81d03af65c3d3a442f38559d3967e28c"
PHONE_NUMBERS = [
    "0951417365", "0959694413", "0829196672", "0659599070"
]
NOTIFY_GROUP_ID = -1002405260670

used_links = set()

client = TelegramClient("truemoney_bot", API_ID, API_HASH)

# ปรับปรุง regex ให้ดักจับลิงก์แม้จะมีข้อความแปลกๆ ปนอยู่
link_pattern = re.compile(r"https?://gift\.truemoney\.com/campaign/\?v=[\w\d]+")

@client.on(events.NewMessage)
async def handler(event):
    message = event.message.message
    print(f"📩 ข้อความที่ได้รับ: {message}")  # Debug

    # ค้นหาลิงก์ที่อยู่ในข้อความ
    matches = link_pattern.findall(message)
    
    if not matches:
        print("🚫 ไม่พบลิงก์ซองในข้อความนี้")
        return

    for angpao_link in matches:
        angpao_code = angpao_link.split("v=")[-1]

        if angpao_code in used_links:
            print(f"⚠️ ซองนี้เคยใช้แล้ว: {angpao_code}")
            continue

        used_links.add(angpao_code)
        print(f"🎁 พบซอง: {angpao_code}")

        for phone in PHONE_NUMBERS:
            success, amount = claim_angpao(angpao_code, phone)
            if success:
                await notify_success(phone, angpao_code, amount)
            else:
                await notify_fail(phone, angpao_code)

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
        print(f"⚠️ Error: {e}")

    return False, 0.00

async def notify_success(phone, code, amount):
    message = f"✅ เบอร์ {phone} ได้รับ {amount:.2f} บาท จากซอง {code}!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

async def notify_fail(phone, code):
    message = f"❌ เบอร์ {phone} รับซอง {code} ไม่สำเร็จ!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

async def main():
    print("🚀 กำลังรันบอท...")
    await client.start()
    print("✅ บอทเชื่อมต่อสำเร็จ!")
    await client.run_until_disconnected()

asyncio.run(main())
