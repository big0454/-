import re
import requests
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl

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

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ (รองรับลิงก์ที่ติดกับตัวอักษรอื่น)
def extract_angpao_codes(text):
    pattern = r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)"
    matches = re.findall(pattern, text)

    # 📌 ตรวจจับกรณีที่ลิงก์ติดตัวอักษรอื่น เช่น "ควดยดมhttps://gift.truemoney.com/campaign?v=..."
    cleaned_text = re.sub(r"[^a-zA-Z0-9:/?=._-]", "", text)  # ลบอักขระที่ไม่ใช่ URL ออก
    matches += re.findall(pattern, cleaned_text)

    return matches

# 📌 ฟังก์ชันส่ง API รับเงิน (ลด timeout ให้ไวขึ้น)
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=2)  # ลด timeout เหลือ 2 วินาที
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

# 📌 ดักจับข้อความทุกประเภท (ข้อความธรรมดา + ลิงก์สีฟ้า + ลิงก์ที่ติดตัวอักษร)
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

# 📌 ดักจับ QR Code จากรูปภาพ
@client.on(events.NewMessage)
async def image_handler(event):
    if event.photo:
        # 📥 ดาวน์โหลดรูปภาพ
        file_path = await event.download_media()

        # 📌 อ่าน QR Code จากรูป
        angpao_codes = scan_qr_code(file_path)

        if angpao_codes:
            await process_angpao(angpao_codes, "QR Code")

        # 🗑️ ลบไฟล์ที่ดาวน์โหลด (ลดพื้นที่เก็บข้อมูล)
        os.remove(file_path)

# 📌 ฟังก์ชันสแกน QR Code
def scan_qr_code(image_path):
    img = cv2.imread(image_path)
    qr_codes = decode(img)

    angpao_codes = []
    for qr in qr_codes:
        text = qr.data.decode("utf-8")
        angpao_codes += extract_angpao_codes(text)

    return angpao_codes

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
