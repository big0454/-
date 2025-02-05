import re
import asyncio
import requests
from telethon import TelegramClient, events

# ✅ ตั้งค่า API Telegram
API_ID = 29316101
API_HASH = "81d03af65c3d3a442f38559d3967e28c"
PHONE_NUMBERS = ["0951417365", "0959694413", "0829196672", "0659599070"]
NOTIFY_GROUP_ID = -1002405260670

# 📌 เก็บซองที่เคยใช้ (กันรับซ้ำ)
used_links = set()

# ✅ สร้าง Telegram Client
client = TelegramClient("truemoney_bot", API_ID, API_HASH)

@client.on(events.NewMessage)
async def handler(event):
    message = event.message.message
    print(f"📩 ข้อความที่ได้รับ: {message}")

    # 🔹 จับลิงก์ซอง (รองรับทุกกรณี)
    link_pattern = r"https?://gift\.truemoney\.com/campaign/\?v=[\w\d]+"
    matches = re.findall(link_pattern, message)

    if matches:
        for angpao_link in matches:
            angpao_code = angpao_link.split("v=")[-1]

            # 🚫 กันซองซ้ำ
            if angpao_code in used_links:
                print(f"⏳ ซองนี้รับไปแล้ว: {angpao_code}")
                continue

            used_links.add(angpao_code)
            print(f"🎁 พบซองใหม่: {angpao_code}")

            for phone in PHONE_NUMBERS:
                success, amount = claim_angpao(angpao_code, phone)
                if success:
                    await notify_success(phone, angpao_code, amount)
                else:
                    await notify_fail(phone, angpao_code)

def claim_angpao(code, phone):
    """ ส่งคำขอรับซองอั่งเปา และดึงจำนวนเงินที่ได้รับ """
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
    """ แจ้งเตือนเมื่อรับเงินสำเร็จ """
    message = f"✅ เบอร์ {phone} ได้รับ {amount:.2f} บาท จากซอง {code}!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

async def notify_fail(phone, code):
    """ แจ้งเตือนเมื่อรับเงินไม่สำเร็จ """
    message = f"❌ เบอร์ {phone} รับซอง {code} ไม่สำเร็จ!"
    await client.send_message(NOTIFY_GROUP_ID, message)
    print(message)

async def main():
    """ เริ่มรันบอท """
    print("🚀 กำลังรันบอท...")
    await client.start()
    print("✅ บอทเชื่อมต่อสำเร็จ!")
    await client.run_until_disconnected()

# ✅ ใช้ asyncio.run() ให้ทำงานถูกต้อง
if __name__ == "__main__":
    asyncio.run(main())
