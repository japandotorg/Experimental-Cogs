from redbot.core.bot import Red

from .core import Downloader


async def setup(bot: Red) -> None:
    cog: Downloader = Downloader(bot)
    await bot.add_cog(cog)
