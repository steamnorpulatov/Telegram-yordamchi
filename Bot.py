import os
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC
from PIL import Image

# ================= SOZLAMALAR =================
BOT_TOKEN = "9200155582:AAGTpgo3RM8DqfuEoGgDyEOC9ptIu4fTbr0"
CHANNEL_ID = "https://t.me/zawenbeats_bass"       # Masalan: @uz_music_vip
CHANNEL_LINK_TEXT = "\n\n🔥 @sizning_kanalingiz" # Postlar tagidagi yozuv
CHANNEL_TITLE_TAG = "@sizning_kanalingiz" # Musiqa nomiga qo'shiladigan nom
ADMIN_ID = 1940953290                     # O'zingizning Telegram ID raqamingiz
COVER_IMAGE = "cover.jpg"                # Musiqa rasmi (oblojka) fayli
# ==============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# 1. Musiqa muqovasini (oblojka) yangilash buyrug'i
@dp.message(Command("setcover"))
async def set_cover_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Musiqalar uchun yangi muqova (oblojka) rasmini yuboring:")

@dp.message(F.photo & (F.caption == "/setcover"))
async def save_cover_with_caption(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    await save_cover_image(message)

async def save_cover_image(message: types.Message):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, "temp_cover.jpg")
    
    img = Image.open("temp_cover.jpg").convert("RGB")
    img.thumbnail((320, 320))
    img.save(COVER_IMAGE, "JPEG", quality=90)
    os.remove("temp_cover.jpg")
    await message.answer("✅ Yangi musiqa muqovasi (oblojka) saqlandi!")

# 2. Musiqa kelganda asosiy jarayon
@dp.message(F.audio)
async def handle_audio(message: types.Message):
    if not is_admin(message.from_user.id):
        return

    status_msg = await message.answer("⏳ Musiqa qayta ishlanmoqda...")
    
    audio = message.audio
    orig_title = audio.title or (audio.file_name.rsplit('.', 1)[0] if audio.file_name else "Musiqa")
    orig_performer = audio.performer or ""

    new_title = f"{orig_title} | {CHANNEL_TITLE_TAG}"
    safe_filename = f"{orig_title} - {CHANNEL_TITLE_TAG}.mp3".replace("/", "_")

    input_path = f"in_{audio.file_id}.mp3"
    preview_ogg_path = f"preview_{audio.file_id}.ogg"
    output_path = f"out_{audio.file_id}.mp3"

    try:
        file = await bot.get_file(audio.file_id)
        await bot.download_file(file.file_path, input_path)

        # A) 30 soniyalik namuna kesish va OGG formatiga o'tkazish (Ovozli xabar uchun)
        sound = AudioSegment.from_file(input_path)
        thirty_sec = sound[:30 * 1000]
        thirty_sec.export(preview_ogg_path, format="ogg", codec="libopus")

        # B) Asosiy musiqani tahrirlash (Nom + Rasm)
        sound.export(output_path, format="mp3", bitrate="320k")
        
        mp3_file = MP3(output_path, ID3=ID3)
        try:
            mp3_file.add_tags()
        except Exception:
            pass

        mp3_file.tags["TIT2"] = TIT2(encoding=3, text=new_title)
        if orig_performer:
            mp3_file.tags["TPE1"] = TPE1(encoding=3, text=orig_performer)

        if os.path.exists(COVER_IMAGE):
            with open(COVER_IMAGE, "rb") as img_file:
                mp3_file.tags["APIC"] = APIC(
                    encoding=3,
                    mime="image/jpeg",
                    type=3,
                    desc="Cover",
                    data=img_file.read()
                )
        mp3_file.save()

        # C) Kanalga ketma-ket yuborish
        # 1. 30 soniyali parcha Ovozli xabar (Voice message) ko'rinishida
        await bot.send_voice(
            chat_id=CHANNEL_ID,
            voice=FSInputFile(preview_ogg_path),
            caption=f"🎧 **Premyera namunasi (30s):** {orig_title}{CHANNEL_LINK_TEXT}",
            parse_mode="Markdown"
        )

        # 2. To'liq musiqa (yangi nom va rasm bilan)
        thumb_file = FSInputFile(COVER_IMAGE) if os.path.exists(COVER_IMAGE) else None
        original_caption = message.caption or ""
        final_caption = f"{original_caption}{CHANNEL_LINK_TEXT}".strip()

        await bot.send_audio(
            chat_id=CHANNEL_ID,
            audio=FSInputFile(output_path, filename=safe_filename),
            title=new_title,
            performer=orig_performer,
            thumbnail=thumb_file,
            caption=final_caption
        )

        await status_msg.edit_text("✅ Namuna (ovozli xabar) va to'liq musiqa kanalga joylandi!")

    except Exception as e:
        await status_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")

    finally:
        for f_path in [input_path, preview_ogg_path, output_path]:
            if os.path.exists(f_path):
                os.remove(f_path)

# 3. Rasm kelganda
@dp.message(F.photo)
async def handle_photo(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    if message.caption and message.caption.strip() == "/setcover":
        await save_cover_image(message)
        return

    caption = f"{message.caption or ''}{CHANNEL_LINK_TEXT}".strip()
    await bot.send_photo(
        chat_id=CHANNEL_ID,
        photo=message.photo[-1].file_id,
        caption=caption
    )
    await message.answer("✅ Rasm kanalga joylandi!")

# 4. Video kelganda
@dp.message(F.video)
async def handle_video(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    caption = f"{message.caption or ''}{CHANNEL_LINK_TEXT}".strip()
    await bot.send_video(
        chat_id=CHANNEL_ID,
        video=message.video.file_id,
        caption=caption
    )
    await message.answer("✅ Video kanalga joylandi!")

# 5. Oddiy matn kelganda
@dp.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    text = f"{message.text}{CHANNEL_LINK_TEXT}"
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=text
    )
    await message.answer("✅ Matnli post kanalga joylandi!")

async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
  
  
