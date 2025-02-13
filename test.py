import re
import asyncio
import aiohttp
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl

# 📌 ตั้งค่าบัญชี Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
notify_group_id = -1002405260670  # ไอดีกลุ่มแจ้งเตือน
admin_id = 7094215368  # ไอดีแอดมินที่เพิ่ม/ลบเบอร์ได้
phone_file = "phone_numbers.txt"

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# 📌 โหลดเบอร์จากไฟล์
def load_phone_numbers():
    if os.path.exists(phone_file):
        with open(phone_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

phone_numbers = load_phone_numbers()

# 📌 บันทึกเบอร์ลงไฟล์
def save_phone_numbers(phone_numbers):
    with open(phone_file, "w") as f:
        f.write("\n".join(phone_numbers) + "\n")

# 📌 ดึงรหัสซองจากข้อความ
def extract_angpao_codes(text):
    pattern = r"https?://\s*gift\.\s*truemoney\.\s*com/\s*campaign/\s*\?\s*v=\s*([a-zA-Z0-9]+)"
    matches = re.findall(pattern, text.replace(" ", ""))
    return list(set(matches))

# 📌 ฟังก์ชันสแกน QR Code
def scan_qr_code(image_path):
    img = cv2.imread(image_path)
    qr_codes = decode(img)

    angpao_codes = set()
    for qr in qr_codes:
        text = qr.data.decode("utf-8")
        angpao_codes.update(extract_angpao_codes(text))

    return list(angpao_codes)

# 📌 แจ้งเตือนไปที่กลุ่ม
async def notify_group(angpao_code, results):
    message = f"พบซองใหม่💥\nลิ้งค์ซอง: https://gift.truemoney.com/campaign/?v={angpao_code}\n\n"
    for phone, status in results:
        message += f"{phone} {'✅ รับสำเร็จ' if status else '❌ รับไม่สำเร็จ'}\n"

    await client.send_message(notify_group_id, message)

# 📌 รับซองแบบเร็วที่สุด
async def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=0.3) as response:
                return phone, response.status == 200
        except Exception:
            return phone, False

# 📌 ประมวลผลซองแบบเร็วที่สุด โดยให้เบอร์สำคัญรับก่อน
async def process_angpao(angpao_code):
    print(f"🎁 พบซอง: {angpao_code}")

    priority_numbers = ["0951417365", "0659599070"]
    other_numbers = [p for p in phone_numbers if p not in priority_numbers]

    # รับซองก่อนเฉพาะเบอร์สำคัญ
    tasks = [claim_angpao(angpao_code, phone) for phone in priority_numbers if phone in phone_numbers]
    priority_results = await asyncio.gather(*tasks)

    # รับซองสำหรับเบอร์อื่น ๆ พร้อมกัน
    tasks = [claim_angpao(angpao_code, phone) for phone in other_numbers]
    other_results = await asyncio.gather(*tasks)

    results = priority_results + other_results
    await notify_group(angpao_code, results)

# 📌 ดักจับข้อความที่มีลิงก์ซองอั่งเปา
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text
    angpao_codes = extract_angpao_codes(text)

    # ดึงลิงก์จากข้อความที่ซ่อนอยู่
    if event.message.entities:
        for entity in event.message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                angpao_codes += extract_angpao_codes(entity.url)

    angpao_codes = list(set(angpao_codes))

    # ถ้าพบซอง รีบส่งไปประมวลผลทันที
    for code in angpao_codes:
        asyncio.create_task(process_angpao(code))

# 📌 ดักจับ QR Code จากรูปภาพ
@client.on(events.NewMessage)
async def image_handler(event):
    if event.photo:
        file_path = await event.download_media()
        angpao_codes = scan_qr_code(file_path)

        if angpao_codes:
            for code in angpao_codes:
                asyncio.create_task(process_angpao(code))

        os.remove(file_path)

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
    elif command == "/remove" and args:
        del_number = args[0]
        if del_number in phone_numbers:
            phone_numbers.remove(del_number)
            save_phone_numbers(phone_numbers)
            await event.reply(f"✅ ลบเบอร์ {del_number} สำเร็จ!")
    elif command == "/list":
        phone_list = "\n".join(phone_numbers) if phone_numbers else "ไม่มีเบอร์ในระบบ"
        await event.reply(f"📜 เบอร์ที่ใช้งานอยู่:\n{phone_list}")

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
