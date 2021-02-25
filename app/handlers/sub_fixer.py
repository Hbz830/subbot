from aiogram.types import Message, ContentType, InputFile, ChatType
from app.misc import dp, bot
from app.plugins import antiflood
import os
import asyncio
from app.plugins.subfixer import SubtitleFix

subfixer = SubtitleFix()


@dp.message_handler(content_types=ContentType.DOCUMENT)
@antiflood.rate_limit(5, "subtitle_fix")
async def get_document_from_user(message: Message):
    if ChatType.is_private(message):
        if message.document.file_name[-4:] == ".srt":
            wait_msg = await message.reply("فایل شما در حال بررسی و تعمیر می‌باشد! لطفا منتظر بمانید...")
            # download the file from telegram
            path = (await bot.download_file_by_id(message.document.file_id,
                                                    destination=f"downloaded/{message.document.file_name}")).name
            with open(path, 'rb') as f:
                lines = f.read((2 ** 10) ** 2)
                f.close()
                lines, enc = subfixer.decode_string(lines)
                os.remove(path)
                with open(path, 'w') as fnew:
                    fnew.write(str(lines))
                    fnew.close()
                    await asyncio.sleep(1)
                    await wait_msg.edit_text("در حال ارسال فایل...")
                    caption = f"انکدینگ فایل: {enc}" \
                                f"\n\n" \
                                f"حروف عربی با حروف فارسی جایگزین شد!\n" \
                                f"علامت‌های سؤال انگلیسی با فارسی جایگزین شد!\n" \
                                f"اعداد، نقطه‌ها، ویرگول و خط‌های دیالوگ‌ها تنظیم شدند!\n\n" \
                                f"@SubsearchsBot | @SubRelease"
                    await bot.send_document(message.chat.id, document=InputFile(path), caption=caption)
                    os.remove(path)
                    await wait_msg.delete()
        else:
            await message.reply("ربات در حال حاظر فقط قابلیت تعمیر فایل‌های زیرنویس با فرمت srt را دارد!")
