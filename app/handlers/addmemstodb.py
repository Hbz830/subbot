# from app.models.user import User
# from aiogram import types
# from app.misc import bot, dp
# from app import config
# from app.utils.redis import BaseRedis
#
# connector = BaseRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB_FSM)
#
#
# @dp.message_handler(commands="add_db")
# async def add_db(message: types.Message):
#     await connector.connect()
#     redis = connector.redis
#
#     user_list = await redis.smembers("members")
#
#     success = 0
#     try:
#         for user_id in user_list:
#             user_id = int(user_id)
#             user = await User.get(user_id)
#             if user is None:
#                 user = await User.create(id=user_id)
#                 success += 1
#     except Exception as e:
#         print(e)
#     await message.reply(f"success: {success}")