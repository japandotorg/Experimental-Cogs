from redbot.core.bot import Red

from .core import TimeTracker


async def setup(bot: Red) -> None:
    cog: TimeTracker = TimeTracker(bot=bot)
    await bot.add_cog(cog)
