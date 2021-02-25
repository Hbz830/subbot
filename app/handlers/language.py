from app.models.user import User
from aiogram import types
from app.misc import dp, bot
from app.locale import locales
from app.plugins.tools import main_keyboard, language_keyboard


@dp.callback_query_handler(lambda query: query.data.startswith("language?"))
async def change_user_language(query: types.CallbackQuery, user: User):
    if types.ChatType.is_private(query.message):
        imarkup = types.InlineKeyboardMarkup()
        up = query.data.replace("language?", "")
        await user.update(lang=up).apply()
        text = locales[user.lang]["texts"]["update_user_language"]
        await query.message.edit_reply_markup(reply_markup=imarkup)

        markup = await main_keyboard(user)

        await bot.send_message(
            chat_id=query.message.chat.id, text=text, reply_markup=markup
        )


@dp.message_handler(lambda message: message.text in ['Language', 'تغییر زبان'])
async def change_user_language_ky(message: types.Message, user: User):
    if types.ChatType.is_private(message):
        markup = await language_keyboard(user)
        text = locales[user.lang]['texts']['lang']

        await message.answer(text=text, reply_markup=markup)
