import re
import asyncio
import requests
from telethon import TelegramClient, events

# ✅ ตั้งค่า API และเบอร์
API_ID = 29316101
API_HASH = "81d03af65c3d3a442f38559d3967e28c"
PHONE_NUMBERS = [
    "0951417365", "0959694413", "0829196672", "0659599070"
]
NOTIFY_GROUP_ID = -1002405260670  # ID กลุ่มที่ต้องการแจ้งเตือน

used_links = set()  # เก็บซองที่เคยรับแล้ว

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", API_ID, API_HASH)

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ (รองรับทุกกรณี)
def extract_angpao_code(text):
    match = re.search(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)
    return match.group(1) if match else None

# 📌 ฟังก์ชันส่ง API รับเงิน
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=10)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        return {"status": {"message": f"Error: {str(e)}"}}

# 📌 ดักข้อความใหม่ที่มีลิงก์ซอง
@client.on(events.NewMessage)
async def handler(event):
    text = event.message.message
    angpao_code = extract_angpao_code(text)

    if angpao_code:
        if angpao_code in used_links:
            print(f"🚫 ซองนี้เคยใช้แล้ว: {angpao_code}")
            return

        used_links.add(angpao_code)
        print(f"🎁 พบซอง: {angpao_code}")

        results = []
        for phone in PHONE_NUMBERS:
            response = claim_angpao(angpao_code, phone)
            if response and "data" in response and "tickets" in response["data"]:
                tickets = response["data"]["tickets"]
                amount_total = sum(float(ticket["amount_baht"]) for ticket in tickets if ticket["mobile"].replace("-", "") == phone)
                status_msg = response["status"].get("message", "สำเร็จ")
            else:
                amount_total = 0.00
                status_msg = "❌ ไม่สามารถดึงข้อมูลได้"

            result_text = f"📲 เบอร์: {phone}\n💰 ได้รับ: {amount_total:.2f} บาท\n📜 สถานะ: {status_msg}"
            results.append(result_text)

        # 📌 แจ้งเตือนในกลุ่ม Telegram
        final_msg = f"🎉 ซองใหม่! 🎁\n🔗 {text}\n\n" + "\n\n".join(results)
        await client.send_message(NOTIFY_GROUP_ID, final_msg)

# 📌 เริ่มรันบอท
async def main():
    print("🚀 กำลังรันบอท...")
    await client.start()
    print("✅ บอทเชื่อมต่อสำเร็จ!")
    await client.run_until_disconnected()

asyncio.run(main())
