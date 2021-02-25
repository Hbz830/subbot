from app.services.apscheduler import scheduler
import asyncio
from app import config
from app.misc import bot, dp
import jdatetime
from api.subscene import Subscene
from aiogram import types
from app.locale import replace_list, locales
import re
import os
from zipfile import ZipFile
from app.models.user import User
from app.misc import redis, temp_redis
from app.handlers.down_sub import send_subtitle

sub = Subscene()


@dp.message_handler(commands="add_release")
async def add_new_release(message: types.Message, user: User):
    if user.role > 0:
        try:
            url = message.text.split()[1]
            title = url.split("/")[4]
            redis.sadd("auto_send_channel", title)
            await message.reply(
                f"this title added: {title}"
            )
        except:
            await message.reply(
                "Error!"
            )


@dp.message_handler(commands="rsend")
async def send_release_manually(message: types.Message, user: User):
     if user.role > 0:
        try:
            url = message.text.split()[1]
            title = url.split("/")[4]

            await send_subtitle(user=None, r_url=url, channel_id=config.RELEASE_CHANNEL)

            await message.reply(
                f"this title has been sent: {title}"
            )
        except Exception as e:
            print(f"Error: {e}")
            await message.reply(
                "Error!"
            )


@dp.message_handler(commands="rem_release")
async def remove_release(message: types.Message, user: User):
    if user.role > 0:
        try:
            title = message.text.split()[1]
            redis.srem("auto_send_channel", title)
            await message.reply(
                f"this title removed: {title}"
            )
        except:
            await message.reply(
                "Error!"
            )


@dp.message_handler(commands="releases")
async def release_list(message: types.Message, user: User):
    if user.role > 0:
        releases = redis.smembers("auto_send_channel")
        text = f"<strong>Releases list:</strong>\n\n"
        c = 1
        for rel in releases:
            text += f"<i>{c}.</i> <code>{rel}</code>\n"
            c += 1
        text += f"\n\nTotal: {len(releases)}"
        await message.reply(text)


async def auto_send_to_channel_0():
    # await bot.send_message(chat_id=183982329, text="Working...")
    results = await sub.check_for_news("https://subf2m.co/browse/latest/all/1", state="auto")

    for result in results:
        title = result['title']
        in_list = redis.sismember("auto_send_channel", title)
        if in_list == 1:
            r_url = result['link']
            resp = await sub.down_page(r_url)
            title = resp["title"]
            try:
                if " - " in title:
                    season = re.sub(f"(.*)- ", "", title)
                    title = title.replace(season, f"{replace_list[season]}")
            except KeyError:
                pass
            imdb = resp["imdb"]
            author_url = resp["author_url"]
            author_name = resp["author_name"]
            download_url = resp["download_url"]
            comments = resp["comments"]
            releases = resp["releases"]

            text = (
                f'<a href="{imdb}">{title}</a>\n'
                f'{releases}\n\n'
                f'نویسنده: <a href="{author_url}">{author_name}</a>\n'
                f'<code>{comments}</code>\n\n'
                f'@SubsearchsBot'
            )

            url_path = r_url.replace("https://subf2m.co/subtitles/", "").replace(
                "/", "_"
            )
            download = await sub.download(download_url, url_path)

            markup = types.InlineKeyboardMarkup()

            bot_user = await bot.me
            bot_username = bot_user.username
            hash_url = hash(r_url)
            redis.set(hash_url, r_url)
            call_back = f"https://t.me/{bot_username}?start=dl_sub--{hash_url}"
            markup.add(
                types.InlineKeyboardButton(
                    text=locales["fa"]["buttons"]["share_sub"], url=call_back,
                )
            )
            zipfile = ZipFile(download)

            if len(zipfile.namelist()) < 2:
                counter = 0
                for i in zipfile.namelist():
                    if counter > 0:
                        text = "@SubsearchsBot"
                        mu = types.InlineKeyboardMarkup()
                    else:
                        mu = markup
                    doc = zipfile.open(i)
                    await bot.send_document(
                        chat_id=config.RELEASE_CHANNEL,
                        document=doc,
                        caption=text,
                        reply_markup=mu,
                    )
                    counter += 1
            else:
                doc = open(download, "rb")
                await bot.send_document(
                    chat_id=config.RELEASE_CHANNEL,
                    document=doc,
                    caption=text,
                    reply_markup=markup,
                )

            os.remove(download)


async def auto_reset_redis_0():
    banner = redis.get("banner_path")
    views = redis.get(f"banner:{banner}")

    members = temp_redis.scard("dailymems")

    joins = temp_redis.scard("dailyjoins")

    downloads = temp_redis.get("daily:downloads")

    await bot.send_message(
        chat_id=config.BOT_CHANNEL,
        text=f"#stats\n\n"
             f"date: {jdatetime.datetime.now()}"
             f"today's stats:\n\n"
             f"members: {members}\n"
             f"banners views: {views}\n"
             f"channel joins: {joins}\n"
             f"Downloads: {downloads}"
    )
    await asyncio.sleep(20)
    temp_redis.flushdb()
    await bot.send_message(
        chat_id=config.BOT_CHANNEL,
        text=f"daily database flushed!"
    )

scheduler.remove_all_jobs()
scheduler.add_job(auto_reset_redis_0, 'cron', hour=22, minute=30, id="auto_redis_reset_0", replace_existing=True)
scheduler.add_job(auto_send_to_channel_0, 'interval', minutes=5, id="auto_check_channel_0", replace_existing=True)
