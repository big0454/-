import re
import requests
import asyncio
from telethon import TelegramClient, events
from PIL import Image
import io
import cv2
import numpy as np
import pyzbar.pyzbar as pyzbar  # ใช้สำหรับสแกน QR Code

# 📌 ตั้งค่าบัญชี Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
phone_numbers = ["0967942956", "0951417365", "0959694413", "0829196672", "0659599070"]
notify_group_id = -1002405260670  # ไอดีกลุ่มที่จะแจ้งเตือน

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ (จับทุกกรณี)
def extract_angpao_codes(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)

# 📌 ฟังก์ชันส่ง API รับเงิน
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=3)  # ลด timeout ให้เร็วขึ้น
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None

# 📌 ฟังก์ชันประมวลผลซองอั่งเปา
async def process_angpao(angpao_codes, original_text):
    for angpao_code in angpao_codes:
        print(f"🎁 พบซอง: {angpao_code}")

        results = []
        tasks = []
        for phone in phone_numbers:
            tasks.append(asyncio.to_thread(claim_angpao, angpao_code, phone))  # ใช้ async เร่งความเร็ว

        responses = await asyncio.gather(*tasks)

        for i, response in enumerate(responses):
            phone = phone_numbers[i]
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

# 📌 ฟังก์ชันสแกน QR Code จากรูปภาพ
def decode_qr_code(image_data):
    try:
        # โหลดภาพจากไบต์
        image = Image.open(io.BytesIO(image_data))
        image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # ใช้ pyzbar สแกน QR Code
        decoded_objects = pyzbar.decode(image)
        for obj in decoded_objects:
            qr_text = obj.data.decode("utf-8")
            if "gift.truemoney.com/campaign/" in qr_text:
                return qr_text  # คืนค่าลิงก์ที่อยู่ใน QR Code
    except Exception as e:
        print(f"⚠️ Error decoding QR Code: {e}")
    
    return None

# 📌 ดักจับข้อความทุกประเภท (Text, Forward, Reply, Caption)
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text  # อ่านข้อความทั้งหมด
    angpao_codes = extract_angpao_codes(text)

    if angpao_codes:
        await process_angpao(angpao_codes, text)

# 📌 ดักจับรูปภาพ (QR Code)
@client.on(events.NewMessage(func=lambda e: e.photo))
async def photo_handler(event):
    photo = await event.download_media(bytes)  # ดาวน์โหลดรูปเป็นไบต์
    qr_link = decode_qr_code(photo)

    if qr_link:
        print(f"📸 พบ QR Code: {qr_link}")
        angpao_codes = extract_angpao_codes(qr_link)
        if angpao_codes:
            await process_angpao(angpao_codes, qr_link)

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()