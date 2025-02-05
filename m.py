import re
import requests
from telethon import TelegramClient, events

# 📌 ตั้งค่าบัญชี Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
phone_numbers = ["0967942956", "0951417365", "0959694413", "0829196672", "0659599070"]
notify_group_id = -1002405260670  # ไอดีกลุ่มที่จะแจ้งเตือน

# 🔥 สร้าง client
client = TelegramClient("my_telegram_session", api_id, api_hash)

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ
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
    text = event.message.text
    angpao_code = extract_angpao_code(text)

    if angpao_code:
        print(f"🎁 พบซอง: {angpao_code}")

        results = []
        for phone in phone_numbers:
            response = claim_angpao(angpao_code, phone)

            if response and "data" in response and "voucher" in response["data"]:
                amount = response["data"]["voucher"].get("amount_baht", "0.00")
                status_msg = response["status"].get("message", "ไม่ทราบสถานะ")
            else:
                amount = "0.00"
                status_msg = "❌ ไม่สามารถดึงข้อมูลได้"

            result_text = f"📲 เบอร์: {phone}\n💰 ได้รับ: {amount} บาท\n📜 สถานะ: {status_msg}"
            results.append(result_text)

        # 📌 แจ้งเตือนในกลุ่ม Telegram
        final_msg = f"🎉 ซองใหม่! 🎁\n🔗 {text}\n\n" + "\n\n".join(results)
        await client.send_message(notify_group_id, final_msg)

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
