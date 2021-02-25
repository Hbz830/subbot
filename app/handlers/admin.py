from app.models.user import User
from app.models.db import db
from aiogram import types
from app.misc import dp, bot
from app import config
from aiogram.utils import exceptions
from sqlalchemy.sql import expression
import asyncio
from app.misc import redis, temp_redis
from loguru import logger


@dp.message_handler(commands='commands')
async def test(message: types.message, user: User):
    if user.role >= 1:
        text = "/stats\n" \
               "/admin {id}\n" \
               "/set_banner_forward (reply)\n" \
               "/set_banner (reply)\n" \
               "/banner\n" \
               "/del_banner\n" \
               "/forward (reply)\n\n" \
               "/add_release\n" \
               "/rem_release\n" \
               "/releases"
        await message.reply(text)


@dp.message_handler(commands="stats")
async def stats(message: types.Message, user: User):
    if user.role >= 1:
        users = await db.func.count(User.id).gino.scalar()
        active_users = await User.query.where(User.active == expression.true()).gino.all()

        # try:
        banner = redis.get("banner_path")
        views = redis.get(f"banner:{banner}")
        # except:
        #     views = "NO banner!"

        # members:
        members = temp_redis.scard("dailymems")

        joins = temp_redis.scard("dailyjoins")

        downloads = temp_redis.get("daily:downloads")

        await message.reply(
            text=f"users: {users}\n"
                 f"active users: {len(active_users)}\n\n"
                 f"today's stats:\n\n"
                 f"members: {members}\n"
                 f"banners views: {views}\n"
                 f"channel joins: {joins}\n"
                 f"Downloads: {downloads}"
        )


@dp.message_handler(commands="admin")
async def meke_admin(message: types.Message):
    if message.from_user.id == config.SUPER_USER:
        user_id = int(message.text.split()[1])
        await User.update.values(role=1).where(
            User.id == user_id).gino.status()
        await message.reply("Done!")


async def down_media(media, media_type):
    if media_type == "photo":
        file_id = media[-1].file_id
        path = f"downloaded/{file_id}.jpg"
        await bot.download_file_by_id(file_id=file_id, destination=path)
    elif media_type == "gif":
        file_id = media.file_id
        path = f"downloaded/{file_id}.gif"
        await bot.download_file_by_id(file_id=file_id, destination=path)
    else:
        path = None

    return path


@dp.message_handler(commands=["set_banner_forward", "set_banner"])
async def banner_forward(message: types.Message):
    if message.from_user.id == config.SUPER_USER:
        if message.reply_to_message:
            if message.text == "/set_banner_forward":
                message_id = message.reply_to_message.message_id
                from_chat = message.reply_to_message.chat.id

                redis.set("banner_path", message_id)
                redis.set(f"banner:from_chat", message.chat.id)
                redis.set(f"banner:{message_id}", "0")

                await bot.forward_message(
                    chat_id=message.chat.id,
                    from_chat_id=message.chat.id,
                    message_id=message_id
                )
                await message.reply(
                    f"banner activated!\n"
                    f"path: {message_id}"
                )
                return
            if message.reply_to_message.photo:
                media = await down_media(message.reply_to_message.photo, "photo")
                caption = message.reply_to_message.caption
                photo = open(media, "rb")
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=caption
                )
            elif message.reply_to_message.animation:
                media = await down_media(message.reply_to_message.animation, "gif")
                caption = message.reply_to_message.caption
                gif = open(media, "rb")
                await bot.send_animation(
                    chat_id=message.chat.id,
                    animation=gif,
                    caption=caption
                )
            else:
                media = False
                caption = message.reply_to_message.text
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=caption
                )

            redis.set(f"banner_path", media)
            redis.set(f"banner_caption", caption)
            redis.set(f"banner:{media}", "0")

            await message.reply(
                f"banner activated!\n"
                f"path: {media}"
            )


@dp.message_handler(commands="banner")
async def send_banner(message: types.Message):
    banner = redis.get("banner_path")
    counts = redis.get(f"banner:{banner}")
    if banner.startswith("downloaded"):
        caption = redis.get("banner_caption")
        caption = caption + f"\n\nsends: {counts}"

        media_t = banner.split(".")[-1]
        if media_t == "jpg":
            photo = open(banner, "rb")
            await bot.send_photo(
                chat_id=message.from_user.id,
                photo=photo,
                caption=caption
            )
        elif media_t == "gif":
            gif = open(banner, "rb")
            await bot.send_animation(
                chat_id=message.from_user.id,
                animation=gif,
                caption=caption
            )
        else:
            await bot.send_message(
                chat_id=message.from_user.id,
                text=caption
            )
    else:
        from_chat = redis.get(f"banner:from_chat")
        await bot.forward_message(
            chat_id=message.chat.id,
            from_chat_id=from_chat,
            message_id=banner
        )
        await message.reply(f"sents: {counts}")


@dp.message_handler(commands="del_banner")
async def delete_banner(message: types.Message):
    if message.from_user.id == config.SUPER_USER:
        banner = redis.get("banner_path")
        counts = redis.get(f"banner:{banner}")

        redis.delete("banner_path")
        redis.delete("banner_caption")
        redis.delete(f"banner:{banner}")
        redis.delete(f"banner:from_chat")

        await message.reply(
            f"Deleted!\n"
            f"this banner was sent to {counts} users."
        )


async def forward_message(user, message):
    want_to_send = message.reply_to_message.message_id
    try:
        await bot.forward_message(
            chat_id=user.id,
            from_chat_id=message.from_user.id,
            message_id=want_to_send,
            disable_notification=True
        )
    except exceptions.BotBlocked:
        # await User.update.values(active=expression.false()).where(
        #     User.id == user.id).gino.status()
        await user.update(active=expression.false()).apply()
    except exceptions.ChatNotFound:
        await user.delete()
    except exceptions.RetryAfter as e:
        logger.warning(f"Telegram Timeout, sleeping for {e.timeout} seconds!")
        await asyncio.sleep(e.timeout)
        return await forward_message(user, message)  # Recursive call
    except exceptions.UserDeactivated:
        await user.delete()
    except exceptions.TelegramAPIError:
        logger.warning(f"message failed, target: {user.id}")
    else:
        return True
    return False


@dp.message_handler(commands="forward")
async def forward_to_all(message: types.Message):
    if message.from_user.id == config.SUPER_USER:
        users = await db.all(User.query)
        if message.reply_to_message:

            msg = await message.reply("sending...")
            failed_count = 0
            success_count = 0
            try:
                for user in users:
                    if await forward_message(user, message):
                        success_count += 1
                        # await User.update.values(active=expression.true()).where(
                        #     User.id == user.id).gino.status()
                        await user.update(active=expression.true()).apply()
                    else:
                        failed_count += 1
                    await asyncio.sleep(.05)  # 20 message per second (Limit: 30 message per second)
                    if (success_count % 1000) == 0:
                        try:
                            await bot.edit_message_text(
                                chat_id=message.chat.id,
                                message_id=msg.message_id,
                                text=f"Sent to {success_count} users."
                            )
                        except:
                            pass
                        await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"error in sending: {e}")
            finally:
                await message.reply("success!\nsee stats on channel.")
                await bot.send_message(
                    chat_id=config.BOT_CHANNEL,
                    text=f"#success\n\nmessage sent to {success_count} users!\n{failed_count} failed!"
                )
