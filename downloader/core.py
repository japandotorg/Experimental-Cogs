from typing import ClassVar, List, cast

import TagScriptEngine as tse

from redbot.core import commands
from redbot.core.bot import Red
from redbot.cogs.downloader.repo_manager import Repo
from redbot.core.utils.chat_formatting import pagify, box
from redbot.cogs.downloader.downloader import Downloader as _Downloader

from ._tagscript import RepoAdapter


class Downloader(_Downloader):
    __doc__ = _Downloader.__doc__

    repo: commands.Group = cast(commands.Group, _Downloader.repo.copy())

    __version__: ClassVar[str] = "1.0.0"

    def __init__(self, bot: Red) -> None:
        super().__init__(bot)
        self.bot: Red = bot
        self.interpreter: tse.Interpreter = tse.Interpreter(
            [tse.LooseVariableGetterBlock()]
        )

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        n = "\n" if "\n\n" not in pre_processed else ""
        return f"{pre_processed}{n}\n" f"Version: {self.__version__}\n"

    def _format_repo(self, repo: Repo, formatting: str) -> str:
        output: tse.Response = self.interpreter.process(
            formatting, {"repo": RepoAdapter(repo)}
        )
        return output.body  # type: ignore

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
