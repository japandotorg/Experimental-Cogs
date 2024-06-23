from typing import Dict, Final

from redbot.cogs.downloader.repo_manager import Repo
from redbot.core.utils.chat_formatting import humanize_list

from TagScriptEngine import Adapter, Verb, escape_content


MISSING: Final[str] = "Missing from info.json"


class RepoAdapter(Adapter):
    def __init__(self, base: Repo) -> None:
        self.object: Repo = base
        self._attributes: Dict[str, str] = {
            "name": self.object.name,
            "url": self.object.clean_url,
            "author": humanize_list(list(self.object.author)),
            "cogs": humanize_list([cog.name for cog in self.object.available_cogs]),
            "branch": getattr(self.object, "branch", "default"),
            "description": getattr(self.object, "description", MISSING),
            "short": getattr(self.object, "short", MISSING),
            "install_msg": getattr(self.object, "install_msg", MISSING),
        }

    def __repr__(self) -> str:
        return "<{} object={}>".format(type(self).__qualname__, self.object)

    def get_value(self, ctx: Verb) -> str:  # type: ignore
        should_escape = False
        if ctx.parameter is None:
            return_value = self.object.name
        else:
            try:
                value = self._attributes[ctx.parameter]
            except KeyError:
                return  # type: ignore
            if isinstance(value, tuple):
                value, should_escape = value
            return_value = str(value) if value is not None else None
        return escape_content(return_value) if should_escape else return_value  # type: ignore
