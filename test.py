import re
import asyncio
import aiohttp
import os
import redis
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

# 🚀 ตั้งค่า Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# 📌 โหลดเบอร์จากไฟล์
def load_phone_numbers():
    if os.path.exists(phone_file):
        with open(phone_file, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    return []

phone_numbers = load_phone_numbers()

# 📌 ดึงรหัสซองจากข้อความ
def extract_angpao_codes(text):
    pattern = r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)"
    return list(set(re.findall(pattern, text)))  # ใช้ `set()` เพื่อลดค่าซ้ำ

# 📌 ส่ง API รับซอง (ใช้ aiohttp แทน requests)
async def claim_angpao(code, phone):
    url = f"https://gift.truemoney.com/campaign/vouchers/{code}/redeem"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {"mobile": phone, "voucher_hash": code}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=payload, headers=headers, timeout=2) as response:
                return await response.json() if response.status == 200 else None
        except Exception:
            return None

# 📌 ประมวลผลซอง
async def process_angpao(angpao_codes):
    tasks = []
    for angpao_code in angpao_codes:
        if redis_client.get(angpao_code):  # กันรับซ้ำ
            continue
        redis_client.setex(angpao_code, 3600, "claimed")

        print(f"🎁 พบซอง: {angpao_code}")

        for phone in phone_numbers:
            tasks.append(claim_angpao(angpao_code, phone))

    responses = await asyncio.gather(*tasks)

    results = []
    for response, phone in zip(responses, phone_numbers):
        if response and "voucher" in response:
            amount = response["voucher"].get("amount_baht", "0.00")
            status_msg = response.get("status", {}).get("message", "สำเร็จ")
        else:
            amount = "0.00"
            status_msg = "❌ ไม่สามารถดึงข้อมูลได้"

        results.append(f"📲 เบอร์: {phone}\n💰 ได้รับ: {amount} บาท\n📜 สถานะ: {status_msg}")

    if results:
        final_msg = f"🎉 ซองใหม่! 🎁\n🔗 **[กดรับซอง](https://gift.truemoney.com/campaign/?v={angpao_code})**\n\n" + "\n\n".join(results)
        await client.send_message(notify_group_id, final_msg, link_preview=False)

# 📌 ดักจับข้อความทุกประเภท
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text
    angpao_codes = extract_angpao_codes(text)

    if event.message.entities:
        for entity in event.message.entities:
            if isinstance(entity, MessageEntityTextUrl):
                angpao_codes += extract_angpao_codes(entity.url)

    angpao_codes = list(set(angpao_codes))
    if angpao_codes:
        await process_angpao(angpao_codes)

# 📌 ดักจับ QR Code จากรูปภาพ
@client.on(events.NewMessage)
async def image_handler(event):
    if event.photo:
        file_path = await event.download_media()
        angpao_codes = scan_qr_code(file_path)

        if angpao_codes:
            await process_angpao(angpao_codes)

        os.remove(file_path)

# 📌 ฟังก์ชันสแกน QR Code
def scan_qr_code(image_path):
    img = cv2.imread(image_path)
    qr_codes = decode(img)

    angpao_codes = set()
    for qr in qr_codes:
        text = qr.data.decode("utf-8")
        angpao_codes.update(extract_angpao_codes(text))

    return list(angpao_codes)

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
