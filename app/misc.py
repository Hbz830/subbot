from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.redis import RedisStorage2
from loguru import logger
from redis import StrictRedis

from app import config

app_dir: Path =Path(__file__).parent.parent

bot = Bot(config.TELEGRAM_TOKEN, parse_mode=types.ParseMode.HTML)
storage = RedisStorage2(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB_FSM)
dp = Dispatcher(bot, storage=storage)

redis = StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB_FSM, decode_responses=True)
temp_redis = StrictRedis(
    host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_TEMP_DB, decode_responses=True
)  # temporary database, will be deleted every day

def setup():
    from app import middlewares
    from app.utils import executor

    middlewares.setup(dp)
    executor.setup()

    logger.info("Configure handlers...")
    import app.handlers
