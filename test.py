import re
import requests
import os
from telethon import TelegramClient, events

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
    if not os.path.exists(phone_file):
        return []
    with open(phone_file, "r") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

# 📌 บันทึกเบอร์ลงไฟล์
def save_phone_numbers(phone_numbers):
    with open(phone_file, "w") as f:
        f.write("\n".join(phone_numbers) + "\n")

# 📌 เบอร์ที่ใช้รับซอง
phone_numbers = load_phone_numbers()

# 📌 ฟังก์ชันดึงรหัสซองจากข้อความ (ไม่เปลี่ยนของเดิม)
def extract_angpao_codes(text):
    return re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)

# 📌 ฟังก์ชันส่ง API รับเงิน (เร่งความเร็ว)
def claim_angpao(code, phone):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone}"
    try:
        response = requests.get(url, timeout=3)  # ลด timeout ให้เร็วขึ้น
        return response.json() if response.status_code == 200 else None
    except Exception:
        return None

# 📌 ฟังก์ชันประมวลผลซองอั่งเปา (ไม่เปลี่ยนของเดิม)
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

# 📌 ดักจับคำสั่งเพิ่ม/ลบเบอร์
@client.on(events.NewMessage(pattern=r"/(add|remove|list) ?(\d{10})?"))
async def manage_phone_numbers(event):
    if event.sender_id != admin_id:
        return  # ❌ ไม่ใช่เจ้าของบอท

    command, phone = event.pattern_match.groups()

    if command == "add" and phone:
        if phone not in phone_numbers:
            phone_numbers.append(phone)
            save_phone_numbers(phone_numbers)
            await event.respond(f"✅ เพิ่มเบอร์ {phone} แล้ว!")
        else:
            await event.respond(f"⚠️ เบอร์ {phone} มีอยู่แล้ว!")

    elif command == "remove" and phone:
        if phone in phone_numbers:
            phone_numbers.remove(phone)
            save_phone_numbers(phone_numbers)
            await event.respond(f"🗑 ลบเบอร์ {phone} เรียบร้อย!")
        else:
            await event.respond(f"⚠️ เบอร์ {phone} ไม่พบ!")

    elif command == "list":
        if phone_numbers:
            await event.respond("📋 รายการเบอร์:\n" + "\n".join(phone_numbers))
        else:
            await event.respond("⚠️ ยังไม่มีเบอร์ในระบบ!")

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
