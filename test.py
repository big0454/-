import re
import requests
import asyncio
from telethon import TelegramClient, events

# ✅ ตั้งค่าบัญชี Telegram
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
owner_id = 7094215368  # 🔥 ไอดีเจ้าของที่สามารถใช้คำสั่งจัดการเบอร์ได้
notify_group_id = -1002405260670  # 🔥 กลุ่มที่จะแจ้งเตือน
phone_file = "phone_numbers.txt"  # 📄 ไฟล์เก็บเบอร์

# ✅ ฟังก์ชันโหลดเบอร์จากไฟล์
def load_phone_numbers():
    try:
        with open(phone_file, "r") as f:
            return [line.strip() for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []

# ✅ ฟังก์ชันบันทึกเบอร์ลงไฟล์
def save_phone_numbers(numbers):
    with open(phone_file, "w") as f:
        f.write("\n".join(numbers) + "\n")

# ✅ ดึงเบอร์ปัจจุบัน
phone_numbers = load_phone_numbers()

# 🔥 สร้าง client
client = TelegramClient("truemoney_bot", api_id, api_hash)

# ✅ ฟังก์ชันดึงรหัสซองจากข้อความ (จับได้ทุกกรณี)
def extract_angpao_codes(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)

# ✅ ฟังก์ชันส่ง API รับเงิน
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=3)  # ⏳ ลด timeout ให้เร็วสุด
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None

# ✅ ฟังก์ชันประมวลผลซองอั่งเปา
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

        # ✅ แจ้งเตือนในกลุ่ม Telegram
        final_msg = f"🎉 ซองใหม่! 🎁\n🔗 {original_text}\n\n" + "\n\n".join(results)
        await client.send_message(notify_group_id, final_msg)

# ✅ ดักจับข้อความทุกประเภท (ยกเว้นรูปภาพ)
@client.on(events.NewMessage)
async def message_handler(event):
    if event.photo:  # ❌ ข้ามรูปภาพ
        return

    text = event.raw_text  # ✅ อ่านข้อความทั้งหมด
    angpao_codes = extract_angpao_codes(text)

    if angpao_codes:
        await process_angpao(angpao_codes, text)

# ✅ ฟังก์ชันเพิ่มเบอร์ (ใช้ได้เฉพาะเจ้าของ)
@client.on(events.NewMessage(pattern=r"^/add (\d{10})$"))
async def add_phone(event):
    if event.sender_id != owner_id:
        return await event.reply("❌ คุณไม่มีสิทธิ์เพิ่มเบอร์")

    new_phone = event.pattern_match.group(1)
    if new_phone in phone_numbers:
        return await event.reply(f"⚠️ เบอร์ {new_phone} มีอยู่แล้ว")

    phone_numbers.append(new_phone)
    save_phone_numbers(phone_numbers)
    await event.reply(f"✅ เพิ่มเบอร์ {new_phone} สำเร็จ")

# ✅ ฟังก์ชันลบเบอร์ (ใช้ได้เฉพาะเจ้าของ)
@client.on(events.NewMessage(pattern=r"^/del (\d{10})$"))
async def del_phone(event):
    if event.sender_id != owner_id:
        return await event.reply("❌ คุณไม่มีสิทธิ์ลบเบอร์")

    del_phone = event.pattern_match.group(1)
    if del_phone not in phone_numbers:
        return await event.reply(f"⚠️ เบอร์ {del_phone} ไม่มีในระบบ")

    phone_numbers.remove(del_phone)
    save_phone_numbers(phone_numbers)
    await event.reply(f"✅ ลบเบอร์ {del_phone} สำเร็จ")

# ✅ ฟังก์ชันดูเบอร์ทั้งหมด (ใช้ได้เฉพาะเจ้าของ)
@client.on(events.NewMessage(pattern=r"^/list$"))
async def list_phones(event):
    if event.sender_id != owner_id:
        return await event.reply("❌ คุณไม่มีสิทธิ์ดูเบอร์")

    phone_list = "\n".join(phone_numbers) if phone_numbers else "⚠️ ยังไม่มีเบอร์ในระบบ"
    await event.reply(f"📋 เบอร์ทั้งหมด:\n\n{phone_list}")

# ✅ เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
