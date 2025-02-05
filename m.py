import re
import asyncio
import requests
from telethon import TelegramClient, events

# 🔑 API ID & HASH
API_ID = 29316101
API_HASH = "81d03af65c3d3a442f38559d3967e28c"

# 📱 เบอร์โทรที่ใช้รับซอง
PHONE_NUMBERS = ["0951417365", "0959694413", "0829196672", "0659599070"]

# 📢 ID กลุ่มที่ต้องการแจ้งเตือน
NOTIFY_GROUP_ID = -1002405260670

# 📌 เก็บซองที่ใช้ไปแล้ว
used_links = set()

# 📡 สร้าง Telegram Client
client = TelegramClient("truemoney_bot", API_ID, API_HASH)

# 🎯 ฟังก์ชันดึงลิงก์จากข้อความ (รองรับทุกแบบ)
def extract_angpao_links(text):
    # 🔹 จับลิงก์ทุกแบบ: ลิงก์ตรง, inline link, ลิงก์ใน HTML หรือ Markdown
    link_pattern = r"(https?://gift\.truemoney\.com/campaign/\?v=[\w\d]+)"
    return re.findall(link_pattern, text)

# 🎯 ฟังก์ชันรับซอง
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        if data.get("status", {}).get("message", "").lower() == "success":
            tickets = data.get("data", {}).get("tickets", [])
            amount_total = sum(
                float(ticket["amount_baht"])
                for ticket in tickets if ticket["mobile"].replace("-", "") == phone
            )
            return True, amount_total
    except Exception as e:
        print(f"⚠️ Error: {e}")

    return False, 0.00

# 🎯 ฟังก์ชันแจ้งเตือนสำเร็จ
async def notify_success(phone, code, amount):
    message = f"✅ เบอร์ {phone} ได้รับ {amount:.2f} บาท จากซอง {code}!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

# 🎯 ฟังก์ชันแจ้งเตือนล้มเหลว
async def notify_fail(phone, code):
    message = f"❌ เบอร์ {phone} รับซอง {code} ไม่สำเร็จ!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

# 🎯 ฟังก์ชันดักจับข้อความใหม่
@client.on(events.NewMessage)
async def handler(event):
    message = event.message.message or ""
    print(f"📩 ข้อความที่ได้รับ: {message}")  # Debug

    # 🔍 ค้นหาลิงก์ซองในข้อความ
    angpao_links = extract_angpao_links(message)
    if not angpao_links:
        return

    for angpao_link in angpao_links:
        angpao_code = angpao_link.split("v=")[-1]

        # 🚫 ข้ามซองที่เคยใช้แล้ว
        if angpao_code in used_links:
            print(f"🚫 ซองนี้เคยใช้แล้ว: {angpao_code}")
            continue

        used_links.add(angpao_code)
        print(f"🎁 พบซอง: {angpao_code}")

        # 📲 ลองรับซองกับทุกเบอร์
        for phone in PHONE_NUMBERS:
            success, amount = claim_angpao(angpao_code, phone)
            if success:
                await notify_success(phone, angpao_code, amount)
            else:
                await notify_fail(phone, angpao_code)

# 🚀 ฟังก์ชันเริ่มต้นบอท
async def main():
    print("🚀 กำลังรันบอท...")
    await client.start()
    print("✅ บอทเชื่อมต่อสำเร็จ!")
    await client.run_until_disconnected()

asyncio.run(main())
