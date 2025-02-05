import re
import requests
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl
from io import BytesIO

# 📌 ตั้งค่าบัญชี Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
notify_group_id = -1002405260670  # ไอดีกลุ่มที่จะแจ้งเตือน
admin_id = 7094215368  # ไอดีของเจ้าของที่สามารถเพิ่ม/ลบเบอร์ได้
phone_file = "phone_numbers.txt"

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# 📌 โหลดเบอร์จากไฟล์
def load_phone_numbers():
    if os.path.exists(phone_file):
        with open(phone_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

# 📌 บันทึกเบอร์ลงไฟล์
def save_phone_numbers(phone_numbers):
    with open(phone_file, "w") as f:
        f.write("\n".join(phone_numbers) + "\n")

# 📌 อ่านเบอร์
phone_numbers = load_phone_numbers()

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ
def extract_angpao_codes(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign\?v=([\w\d]+)", text)

# 📌 ฟังก์ชันส่ง API รับเงิน
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=2)  # ลด timeout เพื่อความเร็ว
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

# 📌 ดักจับข้อความทุกประเภท (ข้อความปกติ, ข้อความสีฟ้า, ลิงก์ซ่อน)
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text  # อ่านข้อความทั้งหมด
    angpao_codes = extract_angpao_codes(text)

    # 📌 ตรวจสอบข้อความที่ฝังลิงก์ (ข้อความสีฟ้า)
    if event.message.entities:
        for entity in event.message.entities:
            if isinstance(entity, MessageEntityTextUrl):  # ตรวจสอบว่าเป็นลิงก์ซ่อน
                angpao_codes += extract_angpao_codes(entity.url)

    if angpao_codes:
        await process_angpao(angpao_codes, text)

# 📌 ฟังก์ชันสแกน QR Code และดึงลิงก์ซอง
def extract_qr_code(image):
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        barcodes = decode(gray)
        for barcode in barcodes:
            url = barcode.data.decode("utf-8")
            if "gift.truemoney.com/campaign/?v=" in url:
                return extract_angpao_codes(url)
    except Exception:
        return []
    return []

# 📌 ดักจับ QR Code ที่ส่งมาเป็นรูปภาพ
@client.on(events.NewMessage)
async def qr_code_handler(event):
    if event.photo:
        img = await event.download_media(BytesIO())
        img = cv2.imdecode(np.frombuffer(img.getvalue(), np.uint8), cv2.IMREAD_COLOR)

        angpao_codes = extract_qr_code(img)
        if angpao_codes:
            await process_angpao(angpao_codes, "📸 ซองจาก QR Code!")

# 📌 คำสั่งเพิ่ม/ลบเบอร์
@client.on(events.NewMessage(pattern=r"/(add|remove|list)"))
async def manage_phone(event):
    global phone_numbers
    if event.sender_id != admin_id:
        return await event.reply("❌ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")

    command, *args = event.text.split()
    if command == "/add" and args:
        new_number = args[0]
        if new_number not in phone_numbers:
            phone_numbers.append(new_number)
            save_phone_numbers(phone_numbers)
            await event.reply(f"✅ เพิ่มเบอร์ {new_number} สำเร็จ!")
        else:
            await event.reply(f"⚠️ เบอร์ {new_number} มีอยู่แล้ว!")

    elif command == "/remove" and args:
        del_number = args[0]
        if del_number in phone_numbers:
            phone_numbers.remove(del_number)
            save_phone_numbers(phone_numbers)
            await event.reply(f"✅ ลบเบอร์ {del_number} สำเร็จ!")
        else:
            await event.reply(f"⚠️ ไม่พบเบอร์ {del_number} ในระบบ!")

    elif command == "/list":
        phone_list = "\n".join(phone_numbers) if phone_numbers else "ไม่มีเบอร์ในระบบ"
        await event.reply(f"📜 เบอร์ที่ใช้งานอยู่:\n{phone_list}")

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
