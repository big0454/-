import re
import requests
from telethon import TelegramClient, events, Button

# 📌 ตั้งค่าบัญชี Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
phone_numbers = ["0967942956", "0951417365", "0959694413", "0829196672", "0659599070"]
notify_group_id = -1002405260670  # ไอดีกลุ่มที่จะแจ้งเตือน

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ (จับได้ทุกกรณี)
def extract_angpao_codes(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)

# 📌 ฟังก์ชันส่ง API รับเงิน
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=5)  # ลด timeout ให้เร็วขึ้น
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None

# 📌 ฟังก์ชันประมวลผลซองอั่งเปา
async def process_angpao(angpao_codes, original_text):
    for angpao_code in angpao_codes:
        print(f"🎁 พบซอง: {angpao_code}")

        results = []
        for phone in phone_numbers:
            response = claim_angpao(angpao_code, phone)

            if response and "data" in response and "voucher" in response["data"]:
                amount = response["data"]["voucher"].get("amount_baht", "0.00")
                status_msg = response["status"].get("message", "สำเร็จ")
            else:
                amount = "0.00"
                status_msg = "❌ ไม่สามารถดึงข้อมูลได้"

            result_text = f"📲 เบอร์: {phone}\n💰 ได้รับ: {amount} บาท\n📜 สถานะ: {status_msg}"
            results.append(result_text)

        # 📌 แจ้งเตือนในกลุ่ม Telegram
        final_msg = f"🎉 ซองใหม่! 🎁\n🔗 {original_text}\n\n" + "\n\n".join(results)
        await client.send_message(notify_group_id, final_msg)

# 📌 ดักจับข้อความทุกประเภท (Text, Forward, Reply, Caption)
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text  # อ่านข้อความทั้งหมด
    angpao_codes = extract_angpao_codes(text)

    if angpao_codes:
        await process_angpao(angpao_codes, text)

# 📌 ดักจับปุ่มกดที่มีลิงก์ซอง
@client.on(events.CallbackQuery)
async def button_handler(event):
    data = event.data.decode("utf-8")  # แปลงข้อมูลปุ่มเป็นข้อความ
    angpao_codes = extract_angpao_codes(data)

    if angpao_codes:
        await process_angpao(angpao_codes, data)

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
