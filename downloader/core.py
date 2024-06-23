import asyncio
import functools
import subprocess
from pathlib import Path
from sys import executable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, ClassVar, Iterable, List, Optional, cast

import TagScriptEngine as tse

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.cogs.downloader.repo_manager import Repo
from redbot.core.utils.menus import close_menu, menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import pagify, box
from redbot.cogs.downloader.downloader import Downloader as _Downloader
from redbot.cogs.downloader.repo_manager import ProcessFormatter

from ._tagscript import RepoAdapter


class Downloader(_Downloader):
    __doc__: Optional[str] = _Downloader.__doc__

    __version__: ClassVar[str] = "1.0.0"

    PIP_INSTALL: ClassVar[str] = "{python} -m pip install -U -t {target} {requirements}"

    repo: commands.Group = cast(commands.Group, _Downloader.repo.copy())

    def __init__(self, bot: Red) -> None:
        super().__init__(bot)
        self.bot: Red = bot
        self.interpreter: tse.Interpreter = tse.Interpreter(
            [tse.LooseVariableGetterBlock()]
        )
        self.__executor: ThreadPoolExecutor = ThreadPoolExecutor(1)
        self.__lock: asyncio.Lock = asyncio.Lock()

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\n" f"Version: {self.__version__}\n"

    def _format_repo(self, repo: Repo, formatting: str) -> str:
        output: tse.Response = self.interpreter.process(
            formatting, {"repo": RepoAdapter(repo)}
        )
        return output.body  # type: ignore

    async def _run(
        self, *args: Any, **kwargs: Any
    ) -> subprocess.CompletedProcess[bytes]:
        async with self.__lock:
            process: (
                subprocess.CompletedProcess
            ) = await asyncio.get_running_loop().run_in_executor(
                self.__executor,
                functools.partial(
                    subprocess.run,
                    *args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    **kwargs,
                ),
            )
            return process

    async def _pip(self, requirements: Iterable[str], target_dir: Path) -> str:
        if not requirements:
            raise commands.BadArgument("Requirements not found.")
        process: subprocess.CompletedProcess[bytes] = await self._run(
            ProcessFormatter().format(
                self.PIP_INSTALL,
                python=executable,
                target=target_dir,
                requirements=requirements,
            )
        )
        return (
            process.stdout.decode("utf-8").strip()
            or process.stderr.decode("utf-8").strip()
        )

    @commands.is_owner()
    @commands.command(require_var_positional=True)
    async def pipinstall(self, ctx: commands.Context, *deps: str) -> None:
        """
        Install a group of dependencies using pip.

        Examples:
        - `[p]pipinstall bs4`
        - `[p]pipinstall py-cpuinfo psutil`

        Improper usage of this command can break your bot, be careful.

        **Arguments**

        - `<deps...>` The package or packages you wish to install.
        """
        async with ctx.typing():
            response: str = await self._pip(deps, self.LIB_PATH)
        embeds: List[discord.Embed] = []
        pages: List[str] = [p for p in pagify(response)]
        for index, page in enumerate(pages):
            embed: discord.Embed = discord.Embed(
                description=box(page), color=await ctx.embed_color()
            )
            embed.set_footer(text="Page {}/{}".format(index + 1, len(pages)))
            embeds.append(embed)
        controls = (
            {"\N{CROSS MARK}": close_menu} if len(embeds) == 1 else DEFAULT_CONTROLS
        )
        await menu(ctx, embeds, controls=controls, timeout=120.0)  # type: ignore

    repo.remove_command("list")

    @repo.command(name="list")
    async def _repo_list(
        self, ctx: commands.Context, *, formatting: str = "{repo}"
    ) -> None:
        """
        List all installed repos.

        You can supply a custom formatting tagscript for each repo.

        The ``{repo}`` block with no parameters returns the repo's full name,
        but passing the attributes listed below to the block payload will return
        that attribute instead.

        **Usage:** ``{repo([attribute])}``

        **Attributes:** ``name``, ``url``, ``author``, ``cogs``, ``branch``,
        ``description``, ``short`` & ``install_msg``
        """
        repos: List[Repo] = sorted(
            self._repo_manager.repos, key=lambda r: str.lower(r.name)
        )
        installed: List[str] = []
        if len(repos) == 0:
            head = "There are no repos installed."
        else:
            if len(repos) > 1:
                head = "#Installed Repos\n"
            else:
                head = "# Installed Repo\n"
            installed = [
                "+ {}: {}".format(item.name, self._format_repo(item, formatting))
                for item in repos
            ]
        joined = f"{head}\n" + "\n".join(installed)
        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page, lang="markdown"))
