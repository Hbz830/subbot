from aiogram import types
from aiogram.dispatcher.filters import CommandStart
from loguru import logger
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from app.misc import dp, bot
from app.models.user import User
from app.locale import locales, problems_text
from app.plugins.tools import extract_unique_code, language_keyboard
from app.handlers.down_sub import send_subtitle
from app.handlers.sub_list import send_sub_list
from app import config
from app.plugins import antiflood
from app.plugins.tools import main_keyboard, check_for_join, latest_pop_keyboard
from sqlalchemy.sql import expression
from app.misc import redis, temp_redis
from aiogram.utils import exceptions
from app.handlers.automation import auto_send_to_channel_0


class Form(StatesGroup):
    get_name = State()
    get_feedback = State()
    answer_feedback = State()


@dp.message_handler(commands="menu")
@antiflood.rate_limit(3, "menu")
async def menu(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        markup = await main_keyboard(user)

        await message.answer(
            text=locales[user.lang]['texts']['menu'],
            reply_markup=markup
        )


@dp.message_handler(lambda message: message.text in ['Send Feedback', 'پشتیبانی'], state="*")
@antiflood.rate_limit(3, "feedback")
async def feedback(message: types.Message, state: FSMContext, user: User):
    if types.ChatType.is_private(message):
        current_state = await state.get_state()
        if current_state is not None:
            # Cancel state and inform user about it
            await state.finish()
        await Form.get_feedback.set()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton(text=locales[user.lang]['buttons']['cancel']))

        await message.reply(text=locales[user.lang]['texts']['feedback'], reply_markup=markup)


# cancel all state process
@dp.message_handler(lambda msg: msg.text in ['cancel', 'لغو'], state="*")
@dp.message_handler(Text(equals='cancel', ignore_case=True), state='*')
@antiflood.rate_limit(2, 'cancel')
async def cancel_handler(message: types.Message, state: FSMContext, user: User):
    if types.ChatType.is_private(message):
        """
        Allow user to cancel any action
        """
        current_state = await state.get_state()
        if current_state is None:
            return

        # Cancel state and inform user about it
        await state.finish()
        # And remove keyboard (just in case)
        markup = await main_keyboard(user)
        await message.reply(locales[user.lang]["texts"]["menu"], reply_markup=markup)


# get feedback from users
@dp.message_handler(state=Form.get_feedback)
async def get_feedback(message: types.Message, state: FSMContext, user: User):
    username = message.from_user.username if message.from_user.username else None
    user_id = message.from_user.id
    user_text = message.text

    markup = await main_keyboard(user)
    await message.reply(text=locales[user.lang]['texts']['message_s_success'], reply_markup=markup)

    ch_markup = types.InlineKeyboardMarkup()
    bot_me = await bot.me
    bot_username = bot_me.username
    ch_markup.add(
        types.InlineKeyboardButton(
            "answer", url=f"https://t.me/{bot_username}?start=answer_feedback--{user_id}"
        )
    )
    text = f"New Feedback:\n\n" \
           f"username: @{username}\n" \
           f"user_id: <a href='tg://user?id={user_id}'>{user_id}</a>\n" \
           f"---------------------\n" \
           f"Text:\n{user_text}"
    await bot.send_message(chat_id=config.BOT_CHANNEL, text=text, reply_markup=ch_markup)
    await state.finish()


# answer to users feedback
@dp.message_handler(state=Form.answer_feedback)
async def answer_feedback(message: types.Message, state: FSMContext, user: User):
    if message.from_user.id == config.SUPER_USER:
        text = f" پیام جدید از طرف پشتیبانی:\n----------------\n {message.text}"
        user_id = redis.get("temp_answer")

        try:
            markup = await main_keyboard(user)
            await bot.send_message(chat_id=user_id, text=text, reply_markup=markup, disable_notification=True)
            await message.reply("Done!")
        except:
            await message.reply("failed!")
        finally:
            redis.delete("temp_answer")
            await state.finish()


@dp.message_handler(CommandStart())
async def cmd_start(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        unique_code = extract_unique_code(message.text)
        await user.update(active=expression.true()).apply()

        if unique_code:
            if unique_code.startswith("answer_feedback--"):
                if message.from_user.id == config.SUPER_USER:
                    user_answ = unique_code.replace('answer_feedback--', '')
                    markupt = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
                    markupt.add("cancel")
                    await Form.answer_feedback.set()
                    redis.set("temp_answer", user_answ)
                    await message.reply("enter the message for {} :".format(user_answ), reply_markup=markupt)
            elif unique_code.startswith("dl_sub--"):
                hash_url = unique_code.replace("dl_sub--", "")
                r_url = redis.get(hash_url)
                await send_subtitle(user=user, r_url=r_url, message=message)
            elif unique_code.startswith("sub_list--"):
                r_url = redis.get(unique_code)
                await send_sub_list(user=user, r_url=r_url, message=message)
            elif unique_code.startswith("inline_join"):
                await start_first(message, user)

        else:
            await start_first(message, user)


async def start_first(message, user):
    text = (
            locales["en"]["texts"]["start_text"]
            + "\n\n"
            + locales["fa"]["texts"]["start_text"]
    )

    markup = await language_keyboard(user)

    try:
        await message.answer(text.format(message.from_user.first_name), reply_markup=markup)
        await user.update(start_conversation=True).apply()
    except (exceptions.BotBlocked, exceptions.UserDeactivated):
        await user.update(active=expression.false()).apply()

@dp.message_handler(lambda message: message.text in ['Help', '/help', 'help', 'راهنما'])
async def cmd_help(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        text = f"{locales[user.lang]['texts']['help_starting']}\n" \
               f"{locales[user.lang]['texts']['search_help']}\n" \
               f"------------------------\n" \
               f"{locales[user.lang]['texts']['help_text']}"

        await message.answer(text=text)


@dp.message_handler(lambda message: message.text in ['Subtitle Problems', 'مشکلات زیرنویس‌ها'])
async def cmd_help(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        text = problems_text

        await message.answer(text=text)


@dp.message_handler(lambda message: message.text in ["latest/popular Subtitles", "زیرنویس‌های اخیر/محبوب"])
async def late_pop_handler(message: types.Message):
    text = "انتخاب کنید:"
    markup = await latest_pop_keyboard()
    await message.answer(text=text, reply_markup=markup)


@dp.message_handler(lambda message: message.text in ['Search Subtitle', 'جستجوی زیرنویس'])
async def search_help(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        text = locales[user.lang]['texts']['search_help']
        await message.answer(text=text)


@dp.message_handler(lambda message: message.text in ['Donate', 'حمایت مالی'])
async def search_help(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        text = locales[user.lang]['texts']['donate_text']
        await message.answer(text=text)


@dp.callback_query_handler(lambda query: query.data == "join_check")
async def join_check(query: types.CallbackQuery, user: User):
    is_joined = await check_for_join(query.from_user.id)
    if is_joined:
        markup = await main_keyboard(user)
        imarkup = types.InlineKeyboardMarkup()
        await query.message.edit_text(locales[user.lang]['texts']['join_confirm'], reply_markup=imarkup)
        await bot.send_message(
            chat_id=query.message.chat.id,
            text=locales[user.lang]['texts']['menu'],
            reply_markup=markup
        )
        temp_redis.sadd("dailyjoins", user.id)
    else:
        return


@dp.errors_handler()
async def error_handler(update: types.Update, exception: Exception):
    try:
        raise exception
    except Exception as e:
        logger.exception("Cause exception {e} in update {update}", e=e, update=update)
