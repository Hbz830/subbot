from app.misc import dp, bot, redis
from aiogram import types
from api.subscene import Subscene
from app.models.user import User
from app.locale import replace_list, locales
import re

sub = Subscene()


@dp.inline_handler(lambda inline_query: len(inline_query.query) == 0)
async def zero_inline_query_handler(inline_query: types.InlineQuery):
    if await check_inline_channel(inline_query):
        return
    markup = types.InlineKeyboardMarkup()
    input_content = types.InputTextMessageContent("زیرنویس‌های محبوب: سریال")
    markup.add(types.InlineKeyboardButton(text="کلیک کنید", switch_inline_query_current_chat="popular:tvshows"))
    item = types.InlineQueryResultArticle(
        id="0",
        title="زیرنویس‌های محبوب: سریال",
        input_message_content=input_content,
        reply_markup=markup
    )

    markup1 = types.InlineKeyboardMarkup()
    input_content1 = types.InputTextMessageContent("زیرنویس‌های محبوب: فیلم")
    markup1.add(types.InlineKeyboardButton(text="کلیک کنید", switch_inline_query_current_chat="popular:movies"))
    item1 = types.InlineQueryResultArticle(
        id="1",
        title="زیرنویس‌های محبوب: فیلم",
        input_message_content=input_content1,
        reply_markup=markup1
    )

    markup2 = types.InlineKeyboardMarkup()
    input_content2 = types.InputTextMessageContent("زیرنویس‌های جدید: سریال")
    markup2.add(types.InlineKeyboardButton(text="کلیک کنید", switch_inline_query_current_chat="latest:tvshows"))
    item2 = types.InlineQueryResultArticle(
        id="2",
        title="زیرنویس‌های جدید: سریال",
        input_message_content=input_content2,
        reply_markup=markup2
    )

    markup3 = types.InlineKeyboardMarkup()
    input_content3 = types.InputTextMessageContent("زیرنویس‌های جدید: فیلم")
    markup3.add(types.InlineKeyboardButton(text="کلیک کنید", switch_inline_query_current_chat="latest:movies"))
    item3 = types.InlineQueryResultArticle(
        id="3",
        title="زیرنویس‌های جدید: فیلم",
        input_message_content=input_content3,
        reply_markup=markup3
    )

    await inline_query.answer(results=[item, item1, item2, item3], switch_pm_parameter="inline_join",
                              switch_pm_text="جستجوی زیرنویس",
                              cache_time=1)


async def check_inline_channel(inline_query):
    user_id = inline_query.from_user.id
    user = await User.get(user_id)
    markup = types.InlineKeyboardMarkup()
    if user is None:
        input_content = types.InputTextMessageContent("/start")
        bot_user = await bot.me
        bot_username = bot_user.username
        markup.add(types.InlineKeyboardButton(text="start", url=f"https://t.me/{bot_username}?start=inline_join"))
        item = types.InlineQueryResultArticle(
            id="0",
            title="برای کار با ربات باید ربات رو start کنید!",
            input_message_content=input_content,
            reply_markup=markup
        )
        await inline_query.answer(results=[item], switch_pm_parameter="inline_join", switch_pm_text="عضویت در ربات",
                                  cache_time=1)
        return True


@dp.inline_handler(lambda inline_query: inline_query.query.startswith("latest:"))
async def inline_handler_latest(inline_query: types.InlineQuery):
    if await check_inline_channel(inline_query):
        return
    text = inline_query.query.replace("latest:", "")
    if text == "tvshows":
        resps = await sub.check_for_news("https://subf2m.co/browse/latest/series/1")
    else:
        resps = await sub.check_for_news("https://subf2m.co/browse/latest/film/1")

    await inline_find_latest_pop(resps, inline_query)


@dp.inline_handler(lambda inline_query: inline_query.query.startswith("popular"))
async def inline_handler_popular(inline_query: types.InlineQuery):
    if await check_inline_channel(inline_query):
        return
    text = inline_query.query.replace("popular:", "")
    if text == "tvshows":
        resps = await sub.check_for_news("https://subf2m.co/browse/popular/series/1")
    else:
        resps = await sub.check_for_news("https://subf2m.co/browse/popular/film/1")

    await inline_find_latest_pop(resps, inline_query)


async def inline_find_latest_pop(resps, inline_query):
    bot_user = await bot.me
    bot_username = bot_user.username

    results = []
    counter = 0
    for resp in resps:
        r_url = resp['link']
        title = resp['title']
        try:
            if " - " in title:
                season = re.sub(f"(.*)- ", "", title)
                season = season.split("(")[0].strip()
                title = title.replace(season, f"{replace_list[season]}")
        except KeyError:
            pass

        markup = types.InlineKeyboardMarkup()
        hash_url = hash(r_url)
        redis.set(hash_url, r_url)
        call_back = f"https://t.me/{bot_username}?start=dl_sub--{hash_url}"
        markup.add(
            types.InlineKeyboardButton(
                text="دانلود", url=call_back,
            )
        )
        date = await replace_date(resp['date'])
        item = types.InlineQueryResultArticle(
            id=f"{counter}",
            title=f"{title}",
            input_message_content=types.InputTextMessageContent(
                f"#popdownload\n\n{title}\n\n<a href='{r_url}'>Url</a>",
            ),
            description=f"{resp['author']}\nدانلود‌ها: {resp['downloads']} | تاریخ: {date}",
            reply_markup=markup
        )
        counter += 1
        results.append(item)

    await inline_query.answer(results=results, cache_time=1)


async def replace_date(date):
    date = date.replace("ago", "قبل")
    date = date.replace("days", "روز")
    date = date.replace("day", "روز")
    date = date.replace("hours", "ساعت")
    date = date.replace("hour", "ساعت")
    date = date.replace("minutes", "دقیقه")
    date = date.replace("minute", "دقیقه")
    date = date.replace("seconds", "ثانیه")
    date = date.replace("second", "ثانیه")
    date = date.replace("months", "ماه")
    date = date.replace("month", "ماه")

    return date
