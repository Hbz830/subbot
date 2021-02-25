from api.subscene import Subscene
from aiogram import types
from app.misc import dp, bot
from app.plugins import antiflood
from aiogram.utils import exceptions
from app import config
from app.models.user import User
import re
import json
from app.locale import locales
from app.locale import replace_list
from app.plugins.tools import check_for_join, join_channel_keyboard
import requests
from app.misc import redis, temp_redis

sub = Subscene()


async def extract_imdb_id(url):  # extract imdb id form url and request to omdb
    try:
        imdb_id = re.search(r"tt(\d+)", url).group()
        omdb_url = f"http://www.omdbapi.com/?i={imdb_id}&apikey={config.OMDB_API_KEY}"
        result = await sub.omdb(omdb_url)
        result = json.loads(result)
        return result
    except AttributeError:
        pass


async def get_from_30nama(text):
    text = text.replace(" ", "+")
    url = f"https://30nama.pw/?s={text}"
    result = await sub.cinama(url)
    return result


async def persian_match(strg):
    reg = re.compile(r"^[\u0600-\u06FF\s]+$")
    m = reg.match(strg)
    if m is not None:
        return True
    else:
        return False



@dp.message_handler(regexp=r"^[\u0600-\u06FF\s]+$")
@antiflood.rate_limit(3, "fa_search")
async def search_persian(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        try:
            if len(message.text) < 40:
                search_query = await get_from_30nama(message.text)
                if len(search_query) == 0:
                    await message.reply(f"نتیجه‌ای برای {message.text} یافت نشد ")
                    return
                markup = types.InlineKeyboardMarkup()

                for title in search_query:
                    titlea = re.search(r"[a-zA-Z ]+", title).group()

                    markup.add(types.InlineKeyboardButton(text=title, callback_data=f"search?{titlea}"))
                await message.answer(text=f"نتایج جستجو برای: {message.text}", reply_markup=markup)
        except:
            pass


@dp.message_handler(lambda message: message.text.startswith("https://subscene.com/"))
async def set_sub_ch(message: types.Message):
    try:
        print("ok")
        if types.ChatType.is_private(message):
            link = message.text
            link_count = link.count("/")
            if (link.startswith('http')) and (link_count == 6):
                is_ok = requests.get(link).status_code
                if is_ok == 200:
                    hash_link = hash(link)

                    redis.set(hash_link, link)

                    bot_me = await bot.me
                    bot_username = bot_me.username
                    start = f"https://t.me/{bot_username}?start=dl_sub--{hash_link}"
                    await message.reply(f"لینک شما آماده شد.\n میتونید لینک رو با بقیه به اشتراک "
                                        f" بزارید تا با کلیک روی اون زیرنویس رو دریافت کنند.\n\n {start}",
                                        disable_web_page_preview=True)
                else:
                    await message.reply(locales.set_sub, disable_web_page_preview=True)
            else:
                await message.reply("لینک را به درستی وارد نکرده‌اید!")
    except:
        pass


# get title from user and search
@dp.message_handler(regexp=r"([a-z]|[A-Z]|[0_9])")
@antiflood.rate_limit(3, "subtitle_search")
async def search(message: types.Message, user: User):
    if message.text.startswith("#popdownload"):
        return
    if types.ChatType.is_private(message):
        if user.role >= 1:
            is_joined = True
        else:
            is_joined = await check_for_join(message.from_user.id)
        if is_joined is False:
            markup = await join_channel_keyboard(user)
            await message.reply(locales[user.lang]['texts']['not_joined'], reply_markup=markup)
            return
        # persian = await persian_match(message.text)
        if message.reply_markup:  # if message is via @imdb
            search_query = message.text.split(" (")[0]
        elif message.entities:  # if message from imdb link
            try:
                imdb_url = message.entities[0].get_text(message.text)
                res = await extract_imdb_id(imdb_url)
                search_query = res["Title"]
            except (TypeError, KeyError):
                await message.answer(locales[user.lang]['texts']['wrong_input'])
                return
        else:  # input message manually
            search_query = message.text
        markup = types.InlineKeyboardMarkup()
        mes = await message.reply(locales[user.lang]["texts"]["wait"])
        result = await sub.search(search_query, message)  # send request to api to searchbytitle
        await bot.send_chat_action(message.chat.id, types.chat.ChatActions.TYPING)

        await bot.send_chat_action(message.chat.id, types.chat.ChatActions.TYPING)

        added_list = []
        for res in result:
            count = res["count"]
            url = res["link"].replace("https://subf2m.co/subtitles/", "")
            if (count < 4) or (url in added_list) or (len(markup.inline_keyboard) > 40):
                continue

            title = res["name"]
            if user.lang == "fa":
                try:
                    if " - " in title:
                        season = re.sub(f"(.*)- ", "", title)
                        title = title.replace(season, f"{replace_list[season]}")
                except KeyError:
                    pass

            in_text = f"{title} ، ({count})"

            hashed_url = hash(url)
            hashed_url = f"sub_list?{hashed_url}"
            temp_redis.set(f"user_last_search:{user.id}", search_query)
            temp_redis.set(hashed_url, url)

            # example: sub_list?-107212765310681969:num?/0
            markup.add(
                types.InlineKeyboardButton(
                    text=in_text, callback_data=f"{hashed_url}:num?/0"
                )
            )
            added_list.append(url)

        await bot.delete_message(chat_id=message.chat.id, message_id=mes.message_id)
        try:
            if len(markup.inline_keyboard) == 0:
                text = locales[user.lang]["texts"]["no_title_found"]
                await message.answer(text)
            else:
                text = locales[user.lang]["texts"]["first_step_search"]
                await message.answer(text, reply_markup=markup)

        except exceptions.BadRequest as e:
            print(type(e))


@dp.callback_query_handler(
    lambda query: query.data.startswith("search?")
)  # get search input from inline keyboard
@antiflood.rate_limit(2, "subtitel_search")
async def search_inline(query: types.CallbackQuery, user: User):
    if types.ChatType.is_private(query.message):
        mes = await query.answer("لطفا منتظر بمانید...")
        markup = types.InlineKeyboardMarkup()
        search_query = query.data.replace("search?", "")
        search_query = search_query.strip()
        result = await sub.search(title=search_query, query=query)

        added_list = []
        for res in result:
            count = res["count"]
            url = res["link"].replace("https://subf2m.co/subtitles/", "")
            if (count < 4) or (url in added_list) or (len(markup.inline_keyboard) > 40):
                continue

            title = res["name"]
            try:
                if " - " in title:
                    season = re.sub(f"(.*)- ", "", title)
                    title = title.replace(season, f"{replace_list[season]}")
            except KeyError:
                pass

            in_text = f"{title} ، ({count})"

            hashed_url = hash(url)
            hashed_url = f"sub_list?{hashed_url}"
            temp_redis.set(f"user_last_search:{user.id}", search_query)
            temp_redis.set(hashed_url, url)

            # example: sub_list?-107212765310681969:num?/0
            markup.add(
                types.InlineKeyboardButton(
                    text=in_text, callback_data=f"{hashed_url}:num?/0"
                )
            )
            added_list.append(url)

        try:
            if len(markup.inline_keyboard) == 0:
                await query.answer("did not find any subs, try again:")
            else:
                await query.message.edit_text("founded subs:", reply_markup=markup)

        except exceptions.BadRequest as e:
            print(type(e))
