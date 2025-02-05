import re
import requests
import asyncio
from telethon import TelegramClient, events

# 📌 ตั้งค่าบัญชี Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
owner_id = 7094215368  # 🔥 ไอดีเจ้าของที่ใช้จัดการเบอร์
notify_group_id = -1002405260670  # 🔥 กลุ่มแจ้งเตือน
phone_file = "phone_numbers.txt"  # 📄 ไฟล์เก็บเบอร์

# 🔥 โหลดเบอร์จากไฟล์
def load_phone_numbers():
    try:
        with open(phone_file, "r") as f:
            return [line.strip() for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []

# 🔥 บันทึกเบอร์ลงไฟล์
def save_phone_numbers(numbers):
    with open(phone_file, "w") as f:
        f.write("\n".join(numbers))

phone_numbers = load_phone_numbers()  # โหลดเบอร์เริ่มต้น

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ
def extract_angpao_codes(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)

# 📌 ฟังก์ชันส่ง API รับเงิน (เร็วสุด)
async def claim_angpao_async(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, timeout=3))  # ⏩ ลด timeout
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None

# 📌 ฟังก์ชันประมวลผลซอง (เร็วขึ้น 3 เท่า)
async def process_angpao(angpao_codes, original_text):
    for angpao_code in angpao_codes:
        print(f"🎁 พบซอง: {angpao_code}")

        tasks = [claim_angpao_async(angpao_code, phone) for phone in phone_numbers]  # ⏩ เรียก API พร้อมกัน
        responses = await asyncio.gather(*tasks)

        results = []
        for phone, response in zip(phone_numbers, responses):
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

# 📌 ดักจับข้อความใหม่
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text
    angpao_codes = extract_angpao_codes(text)

    if angpao_codes:
        await process_angpao(angpao_codes, text)

# 📌 ดักจับปุ่มกด
@client.on(events.CallbackQuery)
async def button_handler(event):
    data = event.data.decode("utf-8")
    angpao_codes = extract_angpao_codes(data)

    if angpao_codes:
        await process_angpao(angpao_codes, data)

# 📌 ฟังก์ชันเพิ่ม/ลบเบอร์ผ่านบอท
@client.on(events.NewMessage)
async def manage_phone_numbers(event):
    global phone_numbers

    if event.sender_id != owner_id:
        return  # ❌ ไม่ใช่เจ้าของ ห้ามใช้คำสั่ง

    text = event.raw_text.strip()

    # ✅ เพิ่มเบอร์
    if text.startswith("!เพิ่มเบอร์"):
        new_number = text.split("!เพิ่มเบอร์", 1)[-1].strip()
        if new_number.isdigit() and new_number not in phone_numbers:
            phone_numbers.append(new_number)
            save_phone_numbers(phone_numbers)
            await event.reply(f"✅ เพิ่มเบอร์สำเร็จ: {new_number}")
        else:
            await event.reply("❌ เบอร์ไม่ถูกต้อง หรือมีอยู่แล้ว")

    # ✅ ลบเบอร์
    elif text.startswith("!ลบเบอร์"):
        del_number = text.split("!ลบเบอร์", 1)[-1].strip()
        if del_number in phone_numbers:
            phone_numbers.remove(del_number)
            save_phone_numbers(phone_numbers)
            await event.reply(f"✅ ลบเบอร์สำเร็จ: {del_number}")
        else:
            await event.reply("❌ เบอร์นี้ไม่มีอยู่ในระบบ")

    # ✅ แสดงเบอร์ทั้งหมด
    elif text.startswith("!เบอร์ทั้งหมด"):
        numbers_text = "\n".join(phone_numbers) if phone_numbers else "ไม่มีเบอร์ในระบบ"
        await event.reply(f"📋 เบอร์ที่ใช้รับซอง:\n{numbers_text}")

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
