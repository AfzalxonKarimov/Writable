"""
Entry point. Sets up the aiogram bot/dispatcher, registers all routers,
and runs a webhook-based aiohttp web server (per our hosting decision:
Render free tier + webhook mode + external keep-alive ping, rather than
polling, since Render is a web-service host).

A /health route is exposed specifically for the external uptime-monitor
ping (UptimeRobot / cron-job.org) to hit every 5-10 minutes, which prevents
Render's free tier from spinning the service down to sleep.
"""
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

import config
from db.database import init_db
from handlers import start, mode_selection, submission_flow, results

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def health_check(request: web.Request) -> web.Response:
    """Hit by the external keep-alive pinger. Cheap, no DB/AI calls."""
    return web.Response(text="ok")


async def on_startup(bot: Bot) -> None:
    try:
        logger.info("on_startup: beginning init_db()")
        await init_db()
        logger.info("on_startup: init_db() completed successfully")

        if config.WEBHOOK_URL:
            logger.info(f"on_startup: calling set_webhook for {config.WEBHOOK_URL}")
            result = await bot.set_webhook(
                url=config.WEBHOOK_URL,
                secret_token=config.WEBHOOK_SECRET,
                drop_pending_updates=True,
            )
            if result:
                logger.info(f"Webhook successfully set to {config.WEBHOOK_URL}")
            else:
                logger.error(
                    f"set_webhook() returned False for {config.WEBHOOK_URL} -- "
                    f"Telegram rejected the request without raising an exception."
                )
            info = await bot.get_webhook_info()
            logger.info(f"getWebhookInfo confirms: url='{info.url}', last_error='{info.last_error_message}'")
        else:
            logger.warning("WEBHOOK_BASE_URL not set -- bot will not receive updates until configured.")
    except Exception:
        # Catch-all so the real failure reason is never silently swallowed.
        logger.exception("on_startup FAILED with an exception:")
        raise


async def on_shutdown(bot: Bot) -> None:
    # Deliberately NOT calling bot.delete_webhook() here. On Render's free
    # tier, the process is stopped/restarted on every inactivity spin-down --
    # if we delete the webhook on every shutdown, the bot stays broken until
    # a manual redeploy, instead of just being briefly slow to wake up.
    # set_webhook() on the next startup re-confirms the same URL safely.
    pass


def create_app() -> web.Application:
    if not config.BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not set. Check your .env file (local) or your "
            "Render Environment variables (deployed)."
        )

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Order matters only in that more specific routers could shadow general
    # ones; here each router is scoped to its own FSM states via filters,
    # so registration order is not load-bearing -- kept in flow order for readability.
    dp.include_router(start.router)
    dp.include_router(mode_selection.router)
    dp.include_router(submission_flow.router)
    dp.include_router(results.router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/health", health_check)

    webhook_handler = SimpleRequestHandler(
        dispatcher=dp, bot=bot, secret_token=config.WEBHOOK_SECRET
    )
    webhook_handler.register(app, path=config.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="0.0.0.0", port=config.PORT)
