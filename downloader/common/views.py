import contextlib
import functools
from typing import TYPE_CHECKING, Any, Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red


class ConfirmButton(discord.ui.Button["UpdateView"]):
    def __init__(self, callback: Any, custom_id: str = "CONFIRM:BUTTON") -> None:
        super().__init__(
            emoji="\N{HEAVY CHECK MARK}\N{VARIATION SELECTOR-16}",
            style=discord.ButtonStyle.green,
            custom_id=custom_id,
        )
        self.callback: functools.partial[Any] = functools.partial(callback, self)  # type: ignore


class CancelButton(discord.ui.Button["UpdateView"]):
    def __init__(self, callback: Any, custom_id: str = "CANCEL:BUTTON") -> None:
        super().__init__(
            emoji="\N{HEAVY MULTIPLICATION X}\N{VARIATION SELECTOR-16}",
            style=discord.ButtonStyle.red,
            custom_id=custom_id,
        )
        self.callback: functools.partial[Any] = functools.partial(callback, self)  # type: ignore


class UpdateView(discord.ui.View):
    def __init__(self, ctx: commands.Context, timeout: float = 120) -> None:
        super().__init__(timeout=timeout)
        self.ctx: commands.Context = ctx

        self._message: Optional[discord.Message] = None
        self.value: Optional[bool] = None

        self.add_item(ConfirmButton(self._confirm))
        self.add_item(CancelButton(self._confirm))

    def disable_items(self) -> None:
        for item in self.children:
            item: discord.ui.Item["UpdateView"]
            if hasattr(item, "style"):
                item.style = discord.ButtonStyle.gray  # type: ignore
            item.disabled = True  # type: ignore

    async def interaction_check(self, interaction: discord.Interaction[Red]) -> bool:  # type: ignore
        if self.ctx.author and self.ctx.author.id != self.ctx.author.id:
            await interaction.response.send_message(
                "You are not authorized to interact with this.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_items()
        with contextlib.suppress(discord.HTTPException):
            if self._message:
                await self._message.edit(view=self)

    async def _send(
        self, ctx: commands.Context, content: Optional[str] = None, **kwargs: Any
    ) -> discord.Message:
        message: discord.Message = await ctx.send(
            content,
            view=self,
            reference=self.ctx.message.to_reference(fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions.none(),
            **kwargs,
        )
        self._message = message
        return message

    @classmethod
    async def confirm(
        cls,
        ctx: commands.Context,
        content: Optional[str] = None,
        timeout: int = 60,
        **kwargs: Any,
    ) -> bool:
        view: "UpdateView" = cls(ctx, timeout)
        await view._send(ctx, content, **kwargs)
        await view.wait()
        return view.value  # type: ignore

    @staticmethod
    async def _confirm(
        button: ConfirmButton, interaction: discord.Interaction[Red]
    ) -> None:
        if TYPE_CHECKING:
            assert isinstance(button.view, UpdateView)
        button.view.value = True
        button.view.stop()
        button.view.disable_items()
        with contextlib.suppress(discord.HTTPException):
            if button.view._message:
                await button.view._message.edit(view=button.view)

    @staticmethod
    async def _cancel(
        button: CancelButton, interaction: discord.Interaction[Red]
    ) -> None:
        if TYPE_CHECKING:
            assert isinstance(button.view, UpdateView)
        button.view.value = False
        button.view.stop()
        button.view.disable_items()
        with contextlib.suppress(discord.HTTPException):
            if button.view._message:
                await button.view._message.edit(view=button.view)
