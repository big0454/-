import asyncio
from telethon import TelegramClient, events
import re
import aiohttp

# ตั้งค่าบัญชี Telegram
API_ID = 29316101
API_HASH = "81d03af65c3d3a442f38559d3967e28c"
SESSION_NAME = "my_telegram_session"

# เบอร์ที่ใช้เติมซอง
PHONE_NUMBERS = ["0951417365", "0829196672", "0659599070", "0959694413"]

# กลุ่มที่ต้องแจ้งเตือน
GROUP_NOTIFY_ID = -1002405260670  

# URL API สำหรับเติมเงิน
API_URL = "https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"

# สร้าง Telegram Client
client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# ฟังก์ชันดักจับลิงก์ซองทุกแบบ
def extract_angpao_links(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign/\??v=([a-zA-Z0-9]+)", text)

# ฟังก์ชันเติมซองพร้อมกัน
async def fetch_angpao(session, code, phone):
    url = API_URL.format(code=code, phone=phone)
    try:
        async with session.get(url) as response:
            data = await response.json()
            status = data.get("status", {}).get("message", "").lower()
            amount = data.get("data", {}).get("my_ticket", {}).get("amount_baht", "ไม่ระบุ")
            return phone, amount if "success" in status else None
    except Exception as e:
        print(f"❌ Error with {phone}: {e}")
        return phone, None

# ดักจับทุกข้อความที่มีลิงก์ซอง
@client.on(events.NewMessage)
async def handler(event):
    message_text = event.raw_text  # ข้อความที่มองเห็น
    found_links = extract_angpao_links(message_text)  # ดึงลิงก์จากข้อความ

    # ✅ ตรวจจับลิงก์ที่ซ่อนอยู่ในข้อความ (inline link)
    if event.message.entities:
        for entity in event.message.entities:
            if isinstance(entity, events.message.MessageEntityTextUrl):
                url = entity.url
                found_links += extract_angpao_links(url)

    if found_links:
        print(f"🔍 พบซอง: {found_links}")  

        async with aiohttp.ClientSession() as session:
            for code in found_links:
                tasks = [fetch_angpao(session, code, phone) for phone in PHONE_NUMBERS]
                results = await asyncio.gather(*tasks)

                success_list = [f"{phone} ({amount} บาท)" for phone, amount in results if amount]
                failed_list = [phone for phone, amount in results if not amount]

                # แจ้งเตือนไปที่กลุ่ม
                status_message = f"🧧 **ซองที่ได้รับ:** https://gift.truemoney.com/campaign?v={code}\n\n"
                if success_list:
                    status_message += f"✅ **เติมสำเร็จ:**\n" + "\n".join(success_list) + "\n\n"
                if failed_list:
                    status_message += f"❌ **เติมไม่สำเร็จ:** {', '.join(failed_list)}"

                await client.send_message(GROUP_NOTIFY_ID, status_message)

# รันบอท
async def main():
    await client.start()
    print("🔄 กำลังรันบอท... (รองรับแชแนล, กลุ่ม, และลิงก์ซ่อน)")
    await client.run_until_disconnected()

asyncio.run(main())