import asyncio
import functools
import subprocess
from pathlib import Path
from sys import executable
from concurrent.futures import ThreadPoolExecutor
from typing import Any, ClassVar, Iterable, List, Optional, Set, Union, cast

import TagScriptEngine as tse

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.cogs.downloader.repo_manager import Repo
from redbot.core.utils.menus import close_menu, menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import pagify, box
from redbot.cogs.downloader.converters import InstalledCog
from redbot.cogs.downloader.downloader import Downloader as _Downloader
from redbot.cogs.downloader.installable import Installable, InstalledModule
from redbot.cogs.downloader.repo_manager import ProcessFormatter

from .common.views import UpdateView
from .common._tagscript import RepoAdapter, CogAdapter


class Downloader(_Downloader):
    __doc__: Optional[str] = _Downloader.__doc__

    __version__: ClassVar[str] = "1.0.0"

    PIP_INSTALL: ClassVar[str] = "{python} -m pip install -U -t {target} {requirements}"

    repo: commands.Group = cast(commands.Group, _Downloader.repo.copy())
    cog: commands.Group = cast(commands.Group, _Downloader.cog.copy())

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

    def _format_cog(
        self, cog: Union[Installable, InstalledModule], formatting: str
    ) -> str:
        output: tse.Response = self.interpreter.process(
            formatting, {"cog": CogAdapter(cog)}
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

    async def _ask_for_cog_reload(
        self, ctx: commands.Context, updated_cognames: Set[str]
    ) -> None:
        updated_cognames &= ctx.bot.extensions.keys()
        if not updated_cognames:
            await ctx.send(
                "None of the updated cogs were previously loaded. Update complete."
            )
            return
        if not ctx.assume_yes:
            message: str = (
                "Would you like to reload the updated cogs?"
                if len(updated_cognames) > 1
                else "Would you like to reload the updated cog?"
            )
            confirm: bool = await UpdateView.confirm(ctx, message)
            if not confirm:
                return
        await ctx.invoke(ctx.bot.get_cog("Core").reload, *updated_cognames)

    @commands.is_owner()
    @commands.command(require_var_positional=True, help=_Downloader.pipinstall.help)
    async def pipinstall(self, ctx: commands.Context, *deps: str) -> None:
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
        self, ctx: commands.Context, *, formatting: str = "{repo(url)}"
    ) -> None:
        """
        List all installed repos.

        Example:
        - `[p]repo list`
        - `[p]repo list {repo(cogs)}`

        **Arguments**

        - `<formatting>` supply custom formatting for each repo.

        The ``{repo}`` block with no parameters returns the repo's full name,
        but passing the attributes listed below to the block parameters will return
        that attribute instead.

        **Usage**: ``{repo([attribute])}``

        **Attributes**: ``name``, ``url``, ``author``, ``cogs``, ``branch``,
            ``description``, ``short`` & ``install_msg``.
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

    cog.remove_command("update")

    @cog.command(name="update", help=_Downloader._cog_update.help)
    async def _cog_update(
        self, ctx: commands.Context, reload: Optional[bool], *cogs: InstalledCog
    ) -> None:
        if reload:
            ctx.assume_yes = True
        await self._cog_update_logic(ctx, cogs=list(cogs))

    cog.remove_command("list")

    @cog.command(name="list")
    async def _cog_list(
        self, ctx: commands.Context, repo: Repo, *, formatting: str = "{cog(short)}"
    ) -> None:
        """List all available cogs from a single repo.

        Example:
        - `[p]cog list 26-Cogs`
        - `[p]cog list Seina-Cogs {cog(min_bot)}`

        **Arguments**

        - `<repo>` The repo to list cogs from.
        - `<formatting>` Supply custom formatting for each cog.

        The `{cog}` block with no parameters returns the cog's name,
        but passing the attributes listed below to the block parameters
        will return the attribute instead.

        **Usage**: ``{cog([attribute])}``

        **Attributes**: ``name``, ``description``, ``short``, ``repo_name``,
            ``commit``, ``author``, ``data_statement``, ``min_bot``, ``max_bot``,
            ``min_python``, ``hidden``, ``required_cogs``, ``requirements``,
            ``tags`` & ``install_msg``.
        """
        installed: List[InstalledModule] = [
            cog for cog in await self.installed_cogs() if cog.repo_name == repo.name
        ]
        available: List[Installable] = [
            cog for cog in repo.available_cogs if not (cog.hidden or cog in installed)
        ]
        installed_string: str = "\n".join(
            "- {}: {}".format(cog.name, self._format_cog(cog, formatting))
            for cog in sorted(installed, key=lambda x: x.name.lower())
        )
        if len(installed) > 1:
            installed_string: str = "# Installed Cogs\n{}".format(installed_string)
        elif installed:
            installed_string: str = "# Installed Cog\n{}".format(installed_string)
        available_string: str = "\n".join(
            "+ {}: {}".format(cog.name, self._format_cog(cog, formatting))
            for cog in sorted(available, key=lambda x: x.name.lower())
        )
        if not available_string:
            cogs: str = "> Available Cogs\nNo cogs are available."
        elif len(available) > 1:
            cogs: str = "> Available Cogs\n{}".format(available_string)
        else:
            cogs: str = "> Available Cogs\\n{}".format(available_string)
        cogs: str = cogs + "\n\n" + installed_string
        for page in pagify(cogs, ["\n"], shorten_by=16):
            await ctx.send(box(page, lang="markdown"))
