import re
import asyncio
import aiohttp
import os
import cv2
import numpy as np
from pyzbar.pyzbar import decode
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityTextUrl
import urllib.parse

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
        with open(phone_file, "r", encoding="utf-8") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

phone_numbers = load_phone_numbers()

# 📌 บันทึกเบอร์ลงไฟล์
def save_phone_numbers(phone_numbers):
    with open(phone_file, "w", encoding="utf-8") as f:
        f.write("\n".join(phone_numbers) + "\n")

# 📌 ดึงรหัสซองจากข้อความ รวมถึงลิงก์ที่ถูกย่อ
def extract_angpao_codes(text):
    decoded_text = urllib.parse.unquote(text)
    pattern = r"https?://(?:[a-zA-Z0-9.-]+/)?gift\\.truemoney\\.com/campaign/\\?v=([a-zA-Z0-9]+)"
    matches = re.findall(pattern, decoded_text.replace(" ", ""))
    return list(set(matches))

# 📌 อ่าน QR Code และดึงลิงก์ซอง
def extract_qr_code(image_path):
    image = cv2.imread(image_path)
    if image is None:
        return []
    decoded_objects = decode(image)
    return [obj.data.decode("utf-8") for obj in decoded_objects]

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
    print("🔄 กำลังรันบอท...")
    priority_numbers = ["0951417365", "0659599070"]
    other_numbers = [p for p in phone_numbers if p not in priority_numbers]
    tasks = [claim_angpao(angpao_code, phone) for phone in priority_numbers if phone in phone_numbers]
    priority_results = await asyncio.gather(*tasks)
    tasks = [claim_angpao(angpao_code, phone) for phone in other_numbers]
    other_results = await asyncio.gather(*tasks)
    results = priority_results + other_results
    await notify_group(angpao_code, results)

# 📌 ดักจับข้อความที่มีลิงก์ซองอั่งเปา
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text
    angpao_codes = extract_angpao_codes(text)
    if angpao_codes:
        for code in angpao_codes:
            asyncio.create_task(process_angpao(code))

# 📌 ดักจับไฟล์ภาพ QR Code
@client.on(events.NewMessage)
async def qr_handler(event):
    if event.photo:
        photo_path = await event.download_media()
        qr_links = extract_qr_code(photo_path)
        angpao_codes = []
        for link in qr_links:
            angpao_codes.extend(extract_angpao_codes(link))
        if angpao_codes:
            for code in angpao_codes:
                asyncio.create_task(process_angpao(code))

# 📌 คำสั่งเพิ่ม/ลบ/เช็คเบอร์
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

