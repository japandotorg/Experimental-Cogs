import os
import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Tuple


def humanize_required_cogs(data: Dict[str, str]) -> List[str]:
    response: List[str] = []
    for key, value in data.items():
        url = value if isinstance(value, str) else None
        formatted = "[{}]({})".format(key, url) if url else key
        response.append(formatted)
    return response


class _ReplaceVars(ABC):

    ENV_VARS: ClassVar[Tuple[str, ...]] = (
        "USERPROFILE",
        "HOME",
        "USERNAME",
        "COMPUTERNAME",
    )

    def __init__(
        self, content: str, reverse: bool = False, replacement: bool = True
    ) -> None:
        self.content: str = content
        self.reverse: bool = reverse
        self.replacement: bool = replacement

        self._replace()

    def __repr__(self) -> str:
        return "<{} reverse={} replacement={}>".format(
            type(self).__qualname__, self.reverse, self.replacement
        )

    def __str__(self) -> str:
        return self.content.strip()
    
    def replace(self) -> str:
        return self.content.strip()

    @abstractmethod
    def _replace(self) -> str:
        raise NotImplementedError


# https://github.com/AAA3A-AAA3A/AAA3A_utils/blob/8ddc5c06be4d43cfabb96cc4cee1733581c38020/AAA3A_utils/cogsutils.py#L61-L86
class ReplaceVars(_ReplaceVars):

    def _replace(self) -> str:
        if not self.reverse:
            if not self.replacement:
                return self.content
            for env_var in self.ENV_VARS:
                if env_var in os.environ:
                    regex = re.compile(re.escape(os.environ[env_var]), re.I)
                    self.content = regex.sub(f"{{{env_var}}}", self.content)
                    regex = re.compile(
                        re.escape(os.environ[env_var].replace("\\", "\\\\")), re.I
                    )
                    self.content = regex.sub(f"{{{env_var}}}", self.content)
                    regex = re.compile(
                        re.escape(os.environ[env_var].replace("\\", "/")), re.I
                    )
                    self.content = regex.sub(f"{{{env_var}}}", self.content)
        else:

            class FakeDict(Dict):
                def __init__(
                    self, *args: Any, env_vars: Tuple[str, ...], **kwargs: Any
                ) -> None:
                    self.env_vars: Tuple[str, ...] = env_vars
                    super().__init__(*args, **kwargs)

                def __missing__(self, key: str) -> str:
                    if key.upper() in self.env_vars and key.upper() in os.environ:
                        return os.environ[key.upper()]
                    return f"{{{key}}}"

            self.content = self.content.format_map(FakeDict(env_vars=self.ENV_VARS))
        return self.content
