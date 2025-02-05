
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

# 📌 ดักจับข้อความและปุ่มตามโค้ดเดิมของคุณ (ไม่มีการเปลี่ยนแปลง)
@client.on(events.NewMessage)
async def message_handler(event):
    text = event.raw_text  
    angpao_codes = re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", text)

    if angpao_codes:
        await process_angpao(angpao_codes, text)

@client.on(events.CallbackQuery)
async def button_handler(event):
    data = event.data.decode("utf-8")  
    angpao_codes = re.findall(r"https?://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)", data)

    if angpao_codes:
        await process_angpao(angpao_codes, data)

# 📌 ฟังก์ชันรับซอง (เหมือนเดิม)
async def process_angpao(angpao_codes, original_text):
    for angpao_code in angpao_codes:
        print(f"🎁 พบซอง: {angpao_code}")

        results = []
        for phone in phone_numbers:
            response = requests.get(f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{angpao_code}/{phone}", timeout=3)

            if response.status_code == 200 and "data" in response.json() and "voucher" in response.json()["data"]:
                amount = response.json()["data"]["voucher"].get("amount_baht", "0.00")
                status_msg = response.json()["status"].get("message", "สำเร็จ")
            else:
                amount = "0.00"
                status_msg = "❌ ไม่สามารถดึงข้อมูลได้"

            result_text = f"📲 เบอร์: {phone}\n💰 ได้รับ: {amount} บาท\n📜 สถานะ: {status_msg}"
            results.append(result_text)

        await client.send_message(notify_group_id, f"🎉 ซองใหม่! 🎁\n🔗 {original_text}\n\n" + "\n\n".join(results))

# 📌 เริ่มรันบอท
print("🔄 กำลังรันบอท...")
with client:
    client.run_until_disconnected()
