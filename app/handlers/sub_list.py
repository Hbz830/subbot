from api.subscene import Subscene
from aiogram import types
from app.misc import dp, bot
from app.plugins import antiflood
from app.models.user import User
import re
from app.locale import locales
from app.misc import redis, temp_redis

sub = Subscene()


# example: sub_list?-107212765310681969:num?/0
@dp.callback_query_handler(lambda query: query.data.startswith("sub_list?"))
@antiflood.rate_limit(3, "sub_list")
async def subtitle_lists(query: types.CallbackQuery, user: User):
    if types.ChatType.is_private(query.message):
        redis_get = query.data.split(":num?/")[0]
        show_round = int(query.data.split(":num?/")[1])
        r_url = temp_redis.get(redis_get)

        await send_sub_list(user=user, r_url=r_url, show_round=show_round, query=query)


async def send_sub_list(user, r_url, show_round=0, query=None, message=None):
    lang = user.lang
    markup = types.InlineKeyboardMarkup()
    r_url = "https://subf2m.co/subtitles/" + r_url

    result = await sub.subtitles(r_url, lang)

    search_q = temp_redis.get(f"user_last_search:{user.id}")

    if show_round == 0:

        r_url = r_url.replace("https://subf2m.co/subtitles/", "")
        bot_user = await bot.me
        bot_username = bot_user.username
        hash_url = f"sub_list--{hash(r_url)}"
        redis.set(hash_url, r_url)
        sub_list_callback = f"https://t.me/{bot_username}?start={hash_url}"
        markup.add(
            types.InlineKeyboardButton(
                text=locales[user.lang]["buttons"]["share_sub"],
                url=sub_list_callback
            ))

    markup.add(
        types.InlineKeyboardButton(
            text=locales[f"{user.lang}"]["buttons"]["search_page_button"],
            callback_data=f"search?{search_q}",
        )
    )

    subtitles = result["subtitles"]
    movie_title = result["title"]
    all_r = len(subtitles)
    counter = 0
    counter += show_round
    counter = 0 if counter < 0 else counter
    added_list = []
    for res in range(counter, all_r):
        if len(markup.inline_keyboard) >= 22:
            if query:
                next_p = query.data.replace(f"num?/{show_round}", f"num?/{counter}")
            else:
                hash_url = hash(r_url)
                next_p = f"sub_list?{hash_url}" + f":num?/{counter}"
            markup.add(
                types.InlineKeyboardButton(
                    text=locales[f"{user.lang}"]["buttons"]["next_page"],
                    callback_data=next_p,
                )
            )
            break
        url = subtitles[res]["link"]
        if url in added_list:
            counter += 1
            continue
        title = subtitles[res]["name"]
        owner = subtitles[res]["owner"]

        # try:
        if "Season" in movie_title:
            try:
                title = re.search(r"S(\d+)E(.*)", title).group()
            except AttributeError:
                pass
            if "720p" or "1080p" in title:
                try:
                    if "720p" in title:
                        title = re.sub(r"\.(.*)\.720p", ".720p", title)
                    elif "1080p" in title:
                        title = re.sub(r"\.(.*)\.1080p", ".1080p", title)
                except AttributeError:
                    pass

        else:
            try:
                tit = movie_title.split()[-1]
                title = re.sub(f"(.*){tit}.", "", title)
            except re.error:
                pass

        hashed_url = hash(url)
        hashed_url = f"down_sub?{hashed_url}"
        temp_redis.set(hashed_url, url)
        # callback_data example: down_sub?6400344912346807335
        markup.add(
            types.InlineKeyboardButton(
                text=f"{title} | {owner}", callback_data=hashed_url
            )
        )
        added_list.append(url)
        counter += 1
    if show_round != 0:
        f_page = query.data.replace(f"num?/{show_round}", f"num?/0")
        markup.add(
            types.InlineKeyboardButton(
                text=locales[f"{user.lang}"]["buttons"]["first_page"],
                callback_data=f_page,
            )
        )

    if len(markup.inline_keyboard) < 3:
        await query.answer(locales[user.lang]['texts']['sub_not_found'])
        return
    text = (locales[user.lang]["texts"]["founded_subs"]).format(result["title"])
    if query:
        await query.message.edit_text(text, reply_markup=markup)
    else:
        await bot.send_message(chat_id=message.chat.id, text=text, reply_markup=markup)
