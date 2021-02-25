from api.subscene import Subscene
from aiogram import types
from app.misc import dp, bot
from app.plugins import antiflood
from app.models.user import User
import re
import os
from app.locale import replace_list
from app.locale import locales
from zipfile import ZipFile
from app.misc import redis, temp_redis
import asyncio

sub = Subscene()


# example: down_sub?6400344912346807335
@dp.callback_query_handler(lambda query: query.data.startswith("down_sub?"))
@antiflood.rate_limit(3, "down_sub")
async def download_sub(query: types.CallbackQuery, user: User):
    if types.ChatType.is_private(query.message):
        r_url = temp_redis.get(query.data)

        await send_subtitle(user=user, r_url=r_url, query=query)


async def send_subtitle(user, r_url, query=None, message=None, channel_id=None):

    markup = types.InlineKeyboardMarkup()

    user_lang = "fa" if user is None else user.lang

    result = await sub.down_page(r_url)
    title = result["title"]
    if user_lang == "fa":
        try:
            if " - " in title:
                season = re.sub(f"(.*)- ", "", title)
                title = title.replace(season, f"{replace_list[season]}")
        except KeyError:
            pass
    imdb = result["imdb"]
    author_url = result["author_url"]
    author_name = result["author_name"].strip()
    download_url = result["download_url"]
    comments = result["comments"]
    releases = result["releases"]

    author = locales[user_lang]['texts']['author']
    comments = comments.replace(">", "").replace("<", "")

    text = (
        f'<a href="{imdb}">{title}</a>\n'
        f'{releases}\n\n'
        f'{author}<a href="{author_url}">{author_name}</a>\n'
        f'<code>{comments}</code>\n\n'
        f'@SubsearchsBot'
    )

    url_path = r_url.replace("https://subf2m.co/subtitles/", "").replace(
        "/", "_"
    )
    download = await sub.download(download_url, url_path)

    bot_user = await bot.me
    bot_username = bot_user.username
    hash_url = hash(r_url)
    redis.set(hash_url, r_url)
    call_back = f"https://t.me/{bot_username}?start=dl_sub--{hash_url}"
    markup.add(
        types.InlineKeyboardButton(
            text=locales[user_lang]["buttons"]["share_sub"], url=call_back,
        )
    )
    if channel_id is None:
        if query:
            chat_id = query.message.chat.id
        else:
            chat_id = message.chat.id
        limit = 4
    else:
        chat_id = channel_id
        limit = 2
    try:
        zipfile = ZipFile(download)
        if len(zipfile.namelist()) < limit:
            counter = 0
            for i in zipfile.namelist():
                if counter > 0:
                    text = "@SubsearchsBot"
                    mu = types.InlineKeyboardMarkup()
                else:
                    mu = markup
                doc = zipfile.open(i)
                await bot.send_document(
                    chat_id=chat_id,
                    document=doc,
                    caption=text,
                    reply_markup=mu,
                )
                counter += 1
        else:
            doc = open(download, "rb")
            await bot.send_document(
                chat_id=chat_id,
                document=doc,
                caption=text,
                reply_markup=markup,
            )
    except:
        if not download.endswith(".zip"):
            download += ".zip"
        doc = open(download, "rb")
        await bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=text,
            reply_markup=markup,
        )

    temp_redis.incr("daily:downloads")
    await asyncio.sleep(1)
    os.remove(download)

    if channel_id is None:
        banner_sent_to_user = temp_redis.get(f"sent_banner_day:{user.id}")
        if banner_sent_to_user is None:
            banner = redis.get("banner_path")

            if banner is not None:
                if banner.startswith("downloaded"):
                    caption = redis.get("banner_caption")
                    media_t = banner.split(".")[-1]
                    if media_t == "jpg":
                        photo = open(banner, "rb")
                        await bot.send_photo(
                            chat_id=user.id,
                            photo=photo,
                            caption=caption
                        )
                    elif media_t == "gif":
                        gif = open(banner, "rb")
                        await bot.send_animation(
                            chat_id=user.id,
                            animation=gif,
                            caption=caption
                        )
                    else:
                        await bot.send_message(
                            chat_id=user.id,
                            text=caption
                        )
                else:
                    from_chat = redis.get(f"banner:from_chat")
                    await bot.forward_message(
                        chat_id=user.id,
                        from_chat_id=from_chat,
                        message_id=banner
                    )
                temp_redis.set(f"sent_banner_day:{user.id}", "1")
                redis.incr(f"banner:{banner}")

        # await bot.send_message(query.message.chat.id, text)
