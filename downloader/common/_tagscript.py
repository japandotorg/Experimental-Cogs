from typing import Dict, Final, Union

from redbot.cogs.downloader.repo_manager import Repo
from redbot.cogs.downloader.installable import Installable, InstalledModule
from redbot.core.utils.chat_formatting import humanize_list

from TagScriptEngine import Adapter, Verb, escape_content

from .utils import humanize_required_cogs


MISSING: Final[Dict[str, str]] = {
    "info": "Missing from info.json",
    "cog": "This cog wasn't installed via downloader",
}


class RepoAdapter(Adapter):
    def __init__(self, base: Repo) -> None:
        self.object: Repo = base
        self._attributes: Dict[str, str] = {
            "name": self.object.name,
            "url": self.object.clean_url,
            "author": humanize_list(list(getattr(self.object, "author", ())))
            or MISSING["info"],
            "cogs": humanize_list([cog.name for cog in self.object.available_cogs]),
            "branch": getattr(self.object, "branch", "default"),
            "description": getattr(self.object, "description", MISSING["info"]),
            "short": getattr(self.object, "short", MISSING["info"]),
            "install_msg": getattr(self.object, "install_msg", MISSING["info"]),
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


class CogAdapter(Adapter):
    def __init__(self, base: Union[Installable, InstalledModule]) -> None:
        self.object: Union[Installable, InstalledModule] = base
        self._attributes: Dict[str, str] = {
            "name": self.object.name,
            "description": getattr(self.object, "description", MISSING["info"]),
            "short": getattr(self.object, "short", MISSING["info"]),
            "repo_name": getattr(self.object, "repo_name", MISSING["cog"]),
            "commit": getattr(self.object, "commit", MISSING["cog"]),
            "author": humanize_list(list(getattr(self.object, "author", ())))
            or MISSING["info"],
            "data_statement": getattr(
                self.object, "end_user_data_statement", MISSING["info"]
            ),
            "min_bot": getattr(self.object, "min_bot_version", "None").__str__(),
            "max_bot": getattr(self.object, "max_bot_version", "None").__str__(),
            "min_python": getattr(self.object, "min_python_version", "None").__str__(),
            "hidden": getattr(self.object, "hidden", False).__str__(),
            "required_cogs": humanize_list(
                humanize_required_cogs(getattr(self.object, "required_cogs", {}))
            )
            or MISSING["info"],
            "requirements": humanize_list(
                list(getattr(self.object, "requirements", ()))
            )
            or MISSING["info"],
            "tags": humanize_list(list(getattr(self.object, "tags", ())))
            or MISSING["info"],
            "install_msg": getattr(self.object, "install_msg", MISSING["info"]),
        }

    def __repr__(self) -> str:
        return "<{} object={}>".format(type(self).__qualname__, self.object)

    def update_attributes(self) -> None:
        additional: Dict[str, str] = {}
        if self.object.repo:
            additional["repo"] = getattr(self.object.repo, "clean_url", MISSING["cog"])
        if isinstance(self.object, InstalledModule):
            additional["pinned"] = self.object.pinned.__str__()
        self._attributes.update(additional)

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
