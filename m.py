import re
import json
import asyncio
import aiohttp
from telethon import TelegramClient, events

# ----[ ตั้งค่าข้อมูลบัญชี ]----
api_id = 29316101
api_hash = "81d03af65c3d3a442f38559d3967e28c"
phone_numbers = ["0951417365", "0959694413", "0829196672", "0659599070"]
notify_group_id = -1002405260670  # ใส่ ID กลุ่ม Telegram

# ----[ สร้างเซสชัน Telegram ]----
client = TelegramClient("bot_session", api_id, api_hash)

# ----[ เก็บซองที่รับไปแล้ว ป้องกันแจ้งซ้ำ ]----
received_codes = set()


# ----[ ฟังก์ชันดึงซองและเติมเงิน ]----
async def fetch_angpao(code):
    url = f"https://store.cyber-safe.pro/api/topup/truemoney/angpaofree/{code}/{phone_numbers[0]}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()


# ----[ ฟังก์ชันจัดการข้อความที่มีลิงก์ซอง ]----
@client.on(events.NewMessage)
async def handler(event):
    text = event.message.message

    # ----[ ดักจับทุกแบบของลิงก์ซอง ]----
    pattern = r"https://gift\.truemoney\.com/campaign/\?v=([a-zA-Z0-9]+)"
    match = re.search(pattern, text)
    
    if not match:
        return  # ไม่ใช่ลิงก์ซอง ไม่ต้องทำอะไร

    code = match.group(1)
    
    if code in received_codes:
        return  # ซองนี้รับไปแล้ว ไม่ต้องแจ้งซ้ำ
    
    received_codes.add(code)  # บันทึกซองที่รับไปแล้ว
    print(f"🎁 พบซองใหม่: {code}")

    # ----[ ดึงข้อมูลซอง ]----
    response = await fetch_angpao(code)

    if response is None or "data" not in response:
        await client.send_message(notify_group_id, f"❌ ซอง {code} รับไม่ได้ หรือหมดอายุ")
        return

    # ----[ คำนวณเงินและเตรียมข้อมูลแจ้งเตือน ]----
    tickets = response["data"].get("tickets", [])
    total_amount = sum(float(ticket.get("amount_baht", 0)) for ticket in tickets)

    console_details = "\n".join(
        f"📌 {ticket['mobile'][:3]}-xxx-{ticket['mobile'][-4:]} ได้รับ {ticket['amount_baht']} บาท"
        for ticket in tickets
    )

    bot_details = "\n".join(
        f"📌 {ticket['mobile']} ได้รับ {ticket['amount_baht']} บาท"
        for ticket in tickets
    )

    # ----[ แสดงผลในคอนโซล และส่งไปยัง Telegram ]----
    print(f"✅ รับซองสำเร็จ {code}\n💰 ยอดรวม: {total_amount:.2f} บาท\n{console_details}")

    await client.send_message(
        notify_group_id,
        f"✅ รับซองสำเร็จ {code}\n💰 ยอดรวม: {total_amount:.2f} บาท\n{bot_details}"
    )


# ----[ เริ่มรันบอท ]----
async def main():
    async with client:
        print("🔄 กำลังรันบอท...")
        await client.run_until_disconnected()


asyncio.run(main())
