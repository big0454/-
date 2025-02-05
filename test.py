import re
import requests
import asyncio
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from telethon import TelegramClient, events, Button

# 📌 ตั้งค่า Telegram API
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
bot_owner_id = 7094215368  # 🔴 เปลี่ยนเป็น Telegram ID ของคุณ
notify_group_id = -1002405260670  # ไอดีกลุ่มที่จะแจ้งเตือน
phone_numbers_file = "phone_numbers.txt"  # ไฟล์เบอร์โทร

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# 📌 โหลดเบอร์โทรจากไฟล์
def load_phone_numbers():
    try:
        with open(phone_numbers_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []

# 📌 บันทึกเบอร์โทรลงไฟล์
def save_phone_number(phone, add=True):
    numbers = set(load_phone_numbers())
    if add:
        numbers.add(phone)
        message = f"✅ เพิ่มเบอร์ {phone} เรียบร้อย"
    else:
        numbers.discard(phone)
        message = f"❌ ลบเบอร์ {phone} เรียบร้อย"

    with open(phone_numbers_file, "w") as f:
        f.write("\n".join(numbers))
    
    return message

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ
def extract_angpao_codes(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)

# 📌 ฟังก์ชันดึงรหัสซองจาก QR Code
def extract_from_qr(image_path):
    image = cv2.imread(image_path)
    qr_codes = decode(image)
    return [obj.data.decode("utf-8") for obj in qr_codes]

# 📌 ฟังก์ชันส่ง API รับเงิน
async def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = await asyncio.to_thread(requests.get, url, timeout=3)  # ใช้ asyncio ให้เร็วขึ้น
        data = response.json() if response.status_code == 200 else None
        return phone, data
    except Exception:
        return phone, None

# 📌 ฟังก์ชันประมวลผลซอง
async def process_angpao(angpao_codes, original_text):
    phone_numbers = load_phone_numbers()
    tasks = [claim_angpao(code, phone) for code in angpao_codes for phone in phone_numbers]
    results = await asyncio.gather(*tasks)

    messages = []
    for phone, response in results:
        if response and "data" in response and "voucher" in response["data"]:
            amount = response["data"]["voucher"].get("amount_baht", "0.00")
            status_msg = response["status"].get("message", "สำเร็จ")
        else:
            amount = "0.00"
            status_msg = "❌ ไม่สามารถดึงข้อมูลได้"

        messages.append(f"📲 เบอร์: {phone}\n💰 ได้รับ: {amount} บาท\n📜 สถานะ: {status_msg}")

    if messages:
        final_msg = f"🎉 ซองใหม่! 🎁\n🔗 {original_text}\n\n" + "\n\n".join(messages)
        await client.send_message(notify_group_id, final_msg)

# 📌 ดักจับข้อความ / Forward / Caption
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text
    angpao_codes = extract_angpao_codes(text)

    if angpao_codes:
        await process_angpao(angpao_codes, text)

    # 📌 คำสั่งเพิ่ม/ลบเบอร์ (เฉพาะเจ้าของบอท)
    if event.sender_id == bot_owner_id:
        if text.startswith("/add "):
            phone = text.replace("/add ", "").strip()
            if re.match(r"^\d{10}$", phone):
                message = save_phone_number(phone, add=True)
            else:
                message = "⚠️ กรุณากรอกเบอร์ให้ถูกต้อง (10 หลัก)"
            await event.respond(message)

        elif text.startswith("/del "):
            phone = text.replace("/del ", "").strip()
            message = save_phone_number(phone, add=False)
            await event.respond(message)

        elif text == "/list":
            phone_list = "\n".join(load_phone_numbers()) or "📭 ยังไม่มีเบอร์ในระบบ"
            await event.respond(f"📋 รายการเบอร์ที่ใช้รับซอง:\n{phone_list}")

# 📌 ดักจับปุ่มกดที่มีลิงก์ซอง
@client.on(events.CallbackQuery)
async def button_handler(event):
    data = event.data.decode("utf-8")
    angpao_codes = extract_angpao_codes(data)
    if angpao_codes:
        await process_angpao(angpao_codes, data)

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
