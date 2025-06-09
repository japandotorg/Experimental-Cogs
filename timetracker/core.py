import datetime, operator, itertools, contextlib, collections  # noqa: E401
from typing import (
    DefaultDict,
    Dict,
    Final,
    List,
    Literal,
    Optional,
    cast,
)

import discord
from redbot.core.bot import Red
from redbot.core.utils import AsyncIter
from redbot.core import Config, commands
from redbot.core.utils.views import ConfirmView, SimpleMenu
from redbot.core.utils.mod import get_audit_reason
from redbot.core.utils.chat_formatting import box, humanize_list, pagify

from .models import Clock
from .utils import LONDON, MAXIMUM_ROLES, ClockType


class TimeTracker(commands.Cog):
    """
    Manually record role assignment and removal times within a server.
    """

    __author__: Final[List[str]] = [
        "[**japan.org**](https://github.com/japandotorg) (`759180080328081450`)"
    ]
    __version__: Final[str] = "0.1.0"

    def __init__(self, bot: Red) -> None:
        self.bot: Red = bot
        self.config: Config = Config.get_conf(
            self, identifier=69_420_666, force_registration=True
        )
        __default_guild: Dict[str, List[int]] = {
            "roles": [],
        }
        __default_member: Dict[str, List[ClockType]] = {"clocks": []}
        self.config.register_guild(**__default_guild)
        self.config.register_member(**__default_member)

        self.cache: DefaultDict[int, Dict[int, Clock]] = (
            collections.defaultdict(dict)
        )

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed: str = super().format_help_for_context(ctx)
        n: str = "\n" if "\n\n" not in pre_processed else ""
        text: List[str] = [
            "{}{}".format(pre_processed, n),
            "**Author:** {}".format(humanize_list(self.__author__)),
            "**Version:** {}".format(str(self.__version__)),
        ]
        return "\n".join(text)

    async def cog_load(self) -> None:
        conf: Dict[
            str, Dict[str, Dict[str, List[ClockType]]]
        ] = await self.config.all_members()
        async for guild, items in AsyncIter(conf.items()):
            async for member, data in AsyncIter(items.items()):
                try:
                    entry: ClockType = data["clocks"][-1]
                    start, end = entry["start"], entry["end"]
                except (IndexError, KeyError):
                    continue
                if not end:
                    clock: Clock = Clock(start=start, end=end)
                    self.cache.setdefault(int(guild), {}).setdefault(
                        int(member), clock
                    )
                    break

    @commands.guild_only()
    @commands.group(
        name="timetrackerset",
        aliases=[
            "clock",
            "clockset",
            "clset",
            "ttset",
        ],
    )
    @commands.admin_or_permissions(administrator=True)
    async def clock(self, _: commands.GuildContext) -> None:
        """
        Base configuration command.
        """

    @clock.command(name="reset", aliases=["delete", "del"])
    async def clock_reset(
        self,
        ctx: commands.GuildContext,
        mode: Literal["all", "user"] = "user",
        member: Optional[discord.User] = None,
    ) -> None:
        """
        Delete Time-Tracker logs for the entire server, or selectively for a specific user.
        """
        if mode.lower() == "all":
            view: ConfirmView = ConfirmView(ctx.author)
            view.message = await ctx.send(
                "Using the **all** mode will remove entries for all the members in this server. Do you wish to continue?",
                view=view,
                reference=ctx.message.to_reference(fail_if_not_exists=False),
                allowed_mentions=discord.AllowedMentions(replied_user=False),
            )
            await view.wait()
            if view.result:
                await self.config.clear_all_members(ctx.guild)
                await ctx.send(
                    "Successfully clered time-tracker entries for all the members in this server.",
                    reference=view.message.to_reference(
                        fail_if_not_exists=False
                    ),
                )
            else:
                await ctx.send(
                    "Cancelled...",
                    reference=view.message.to_reference(
                        fail_if_not_exists=False
                    ),
                )
        elif mode.lower() == "user" and member:
            view: ConfirmView = ConfirmView(ctx.author)
            view.message = await ctx.send(
                "Using this command will remove all the entries for **{0.display_name}** (`{0.id}`). Do you wish to continue?".format(
                    member
                ),
                view=view,
                reference=ctx.message.to_reference(fail_if_not_exists=False),
                allowed_mentions=discord.AllowedMentions(replied_user=False),
            )
            await view.wait()
            if view.result:
                await self.config.member_from_ids(
                    ctx.guild.id, member.id
                ).clear()
                await ctx.send(
                    "Successfully clered time-tracker entries for **{0.display_name}** (`{0.id}`) in this server.".format(
                        member
                    ),
                    reference=view.message.to_reference(
                        fail_if_not_exists=False
                    ),
                )
            else:
                await ctx.send(
                    "Cancelled...",
                    reference=view.message.to_reference(
                        fail_if_not_exists=False
                    ),
                )
        else:
            raise commands.UserFeedbackCheckFailure("Invalid mode used.")

    @clock.command(name="add")
    async def clock_add(
        self,
        ctx: commands.GuildContext,
        roles: commands.Greedy[discord.Role],
    ) -> None:
        """Add one or more roles to the timr-tracker assignment list."""
        async with ctx.typing(), self.config.guild(ctx.guild).roles() as config:
            config: List[int]
            if len(roles) >= MAXIMUM_ROLES:
                raise commands.UserFeedbackCheckFailure(
                    "Cannot have more than {} roles configured in a server.".format(
                        MAXIMUM_ROLES
                    )
                )
            if len(config) >= MAXIMUM_ROLES:
                raise commands.UserFeedbackCheckFailure(
                    "Can only have **{}** roles configured in a server.".format(
                        MAXIMUM_ROLES
                    )
                )
            if len(list(itertools.chain(config, roles))) >= MAXIMUM_ROLES:
                raise commands.UserFeedbackCheckFailure(
                    (
                        "Could not add any more roles to the configuration.\n"
                        "This server already has **{}** roles configured, "
                        "and you're trying to add **{}** more, "
                        "a single server can only have **{}** roles configured at once.\n"
                        "You can only add **{}** more roles to the configuration list, "
                        "unless one or more roles are removed."
                    ).format(
                        len(config),
                        len(roles),
                        MAXIMUM_ROLES,
                        MAXIMUM_ROLES - len(config),
                    )
                )
            async for role in AsyncIter(roles):
                if role not in config:
                    config.append(role.id)
        await ctx.send(
            "Successfully added the {} role{} to the configuration.".format(
                humanize_list([role.mention for role in roles]),
                "s" if len(roles) > 1 else "",
            ),
            reference=ctx.message.to_reference(fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(
                roles=False, replied_user=False
            ),
        )

    @clock.command(name="remove")
    async def clock_remove(
        self,
        ctx: commands.GuildContext,
        roles: commands.Greedy[discord.Role],
    ) -> None:
        """Remove one or more roles from the timr-tracker assignment list."""
        async with ctx.typing(), self.config.guild(ctx.guild).roles() as config:
            config: List[int]
            if not any(role in config for role in roles):
                raise commands.UserFeedbackCheckFailure(
                    "The role{} provided {} not in the configuration.".format(
                        "s" if len(roles) > 1 else "",
                        "are" if len(roles) > 1 else "is",
                    )
                )
            if len(roles) >= MAXIMUM_ROLES:
                raise commands.UserFeedbackCheckFailure(
                    (
                        "Cannot have more than {0} roles configured in a server.\n"
                        "So removing more than {0} roles doesn't seem possible, does it?"
                    ).format(MAXIMUM_ROLES)
                )
            if not config:
                raise commands.UserFeedbackCheckFailure(
                    "There doesn't seem to be any roles configured for this server."
                )
            if len(roles) > len(config):
                raise commands.UserFeedbackCheckFailure(
                    (
                        "Cannot remove more roles than there are configured, "
                        "there are only {} role{} configured right now.\n"
                        "{}"
                    ).format(
                        len(config),
                        "s" if len(config) > 1 else "",
                        box(
                            "\n".join(
                                [
                                    "{}. {}".format(idx + 1, role)
                                    async for idx, role in AsyncIter(
                                        enumerate(config)
                                    )
                                ]
                            ),
                            lang="js",
                        ),
                    )
                )
            async for role in AsyncIter(roles):
                if role in config:
                    config.append(role.id)
        await ctx.send(
            "Successfully removed the {} role{} from the configuration.".format(
                humanize_list([role.mention for role in roles]),
                "s" if len(roles) > 1 else "",
            ),
            reference=ctx.message.to_reference(fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(
                roles=False, replied_user=False
            ),
        )

    @clock.command(name="list")
    async def clock_list(self, ctx: commands.GuildContext) -> None:
        """Show the configured assignement roles for the current server!"""
        async with ctx.typing():
            conf: List[int] = await self.config.guild(ctx.guild).roles()
            pages: List[str] = []
            async for rid in AsyncIter(conf):
                try:
                    role: discord.Role = await commands.RoleConverter().convert(
                        ctx, str(rid)
                    )
                except commands.BadArgument as error:
                    raise commands.UserFeedbackCheckFailure(
                        (
                            "Uh Oh, something went wrong - {error}\n"
                            "Make sure to remove the `{role}` role using the "
                            "`{prefix}clock remove {role}` command."
                        ).format(error=error, prefix=ctx.clean_prefix, role=rid)
                    )
                pages.append("{} (`{}`)".format(role.mention, role.id))
            resolved: pagify = pagify(
                "\n".join(
                    [
                        "{}. {}".format(idx + 1, role)
                        async for idx, role in AsyncIter(enumerate(pages))
                    ]
                )
            )
            embeds: List[discord.Embed] = []
            async for desc in AsyncIter(resolved):
                embed: discord.Embed = discord.Embed(
                    title="Configured roles for Time Tracker!",
                    description=desc,
                    color=await ctx.embed_color(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_thumbnail(url=getattr(ctx.guild.icon, "url", None))
                embeds.append(embed)
        await SimpleMenu(embeds, disable_after_timeout=True).start(ctx)

    @commands.guild_only()
    @commands.command(aliases=["clockedin", "cin"])
    @commands.bot_has_permissions(manage_roles=True)
    async def clockin(self, ctx: commands.GuildContext) -> None:
        """
        Initiate time tracking for this server, configured roles will be assigned upon successful clock-in.
        """
        async with ctx.typing():
            cur: Dict[int, Clock] = self.cache.setdefault(ctx.guild.id, {})
            if cur.get(ctx.author.id, None):
                raise commands.UserFeedbackCheckFailure(
                    "{} you are already clocked in, make sure to `{}clockout` first.".format(
                        ctx.author.mention, ctx.clean_prefix
                    )
                )
            try:
                roles: List[discord.Role] = [
                    await commands.RoleConverter().convert(ctx, str(role))
                    async for role in AsyncIter(
                        await self.config.guild(ctx.guild).roles()
                    )
                ]
            except commands.BadArgument as bad:
                raise commands.UserFeedbackCheckFailure(
                    "Failed to convert one of the configured roles.\n{}".format(
                        bad
                    )
                )
            if not roles:
                raise commands.UserFeedbackCheckFailure(
                    "This server has not configured any clocking roles yet."
                )
            with contextlib.suppress(discord.HTTPException):
                await ctx.author.add_roles(
                    *roles,
                    reason=get_audit_reason(ctx.author, reason="clocked in."),
                )
            clock: Clock = Clock()
            self.cache.setdefault(ctx.guild.id, {}).setdefault(
                ctx.author.id, clock
            )
            async with self.config.member(ctx.author).clocks() as clocks:
                cast(List[ClockType], clocks).append(await clock.to_json())
        await ctx.send(
            embed=discord.Embed(
                title="CLOCKED IN",
                description=(
                    "Someone looks busy!\n\n"
                    "{} - You are now clocked in.\n\n"
                    "The timer has started.\n\n"
                    "You have been provided the {} role{}."
                ).format(
                    ctx.author.mention,
                    humanize_list([role.mention for role in roles]),
                    "s" if len(roles) > 1 else "",
                ),
                color=await ctx.embed_color(),
            ).set_thumbnail(
                url="https://r2.fivemanage.com/pa0Dd2d5DbmYV3dBJjYIV/clock-in.png"
            ),
            reference=ctx.message.to_reference(fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(replied_user=False),
        )

    @commands.guild_only()
    @commands.command(aliases=["clockedout", "cout"])
    @commands.bot_has_permissions(manage_roles=True)
    async def clockout(self, ctx: commands.GuildContext) -> None:
        """
        Clock out from the time tracker for this server, configured roles will be removed upon successful clock-out.
        """
        async with ctx.typing():
            cur: Dict[int, Clock] = self.cache.setdefault(ctx.guild.id, {})
            if not (clock := cur.get(ctx.author.id, None)):
                raise commands.UserFeedbackCheckFailure(
                    "{} you're not clocked in yet, make sure to `{}clockin` first.".format(
                        ctx.author.mention, ctx.clean_prefix
                    )
                )
            try:
                roles: List[discord.Role] = [
                    await commands.RoleConverter().convert(ctx, str(role))
                    async for role in AsyncIter(
                        await self.config.guild(ctx.guild).roles()
                    )
                ]
            except commands.BadArgument as bad:
                raise commands.UserFeedbackCheckFailure(
                    "Failed to convert one of the configured roles.\n{}".format(
                        bad
                    )
                )
            if not roles:
                raise commands.UserFeedbackCheckFailure(
                    "This server has not configured any clocking roles yet."
                )
            with contextlib.suppress(discord.HTTPException):
                await ctx.author.remove_roles(
                    *roles,
                    reason=get_audit_reason(ctx.author, reason="clocked out."),
                )
            clock.end = datetime.datetime.now(LONDON)
            async with self.config.member(ctx.author).clocks() as clocks:
                last: int = len(clocks) - 1
                del clocks[last]
                clocks.insert(last, await clock.to_json())
            with contextlib.suppress(KeyError):
                del self.cache[ctx.guild.id][ctx.author.id]
            difference: datetime.timedelta = clock.end - clock.start
            total: int = int(difference.total_seconds())
            hours, seconds = total // 3600, total % 3600
            minutes: int = seconds // 60
            parts: List[str] = []
            if hours > 0:
                parts.append(
                    "{} hour{}".format(hours, "s" if hours > 1 else "")
                )
            if minutes > 0:
                parts.append(
                    "{} minute{}".format(minutes, "s" if minutes > 1 else "")
                )
            if not parts:
                parts.append("less than a minute")

        await ctx.send(
            embed=discord.Embed(
                description=(
                    "{author} - You are now clocked out.\n\n"
                    "The timer has ended.\n\n"
                    "The {roles} role{plural} {was_or_were} removed."
                ).format(
                    author=ctx.author.mention,
                    roles=humanize_list([role.mention for role in roles]),
                    plural="s" if len(roles) > 1 else "",
                    was_or_were="were" if len(roles) > 1 else "was",
                ),
                color=await ctx.embed_color(),
            )
            .set_thumbnail(
                url="https://r2.fivemanage.com/pa0Dd2d5DbmYV3dBJjYIV/clock-out.png"
            )
            .set_footer(
                text="You were clocked in for {}".format(humanize_list(parts))
            ),
            reference=ctx.message.to_reference(fail_if_not_exists=False),
            allowed_mentions=discord.AllowedMentions(replied_user=False),
        )

    @commands.guild_only()
    @commands.command(aliases=["ttrack", "tt"])
    @commands.bot_has_permissions(manage_roles=True)
    @commands.admin_or_permissions(manage_guild=True)
    async def timetracker(
        self,
        ctx: commands.GuildContext,
        *,
        member: discord.Member = commands.parameter(
            default=operator.attrgetter("author"),
            displayed_default="<you>",
            converter=discord.Member,
        ),
    ) -> None:
        """
        Check clock in and out entries for a specific member (defaults to the author).
        """
        async with ctx.typing():
            conf: List[ClockType] = await self.config.member(member).clocks()
            if not conf:
                raise commands.UserFeedbackCheckFailure(
                    (
                        "**{0.display_name}** (`{0.id}`) has not clocked "
                        "in even once yet since the last reset."
                    ).format(ctx.author)
                )
            clocks: List[str] = []
            duration: datetime.timedelta = datetime.timedelta()
            async for clk in AsyncIter(conf):
                clock: Clock = Clock(**clk)
                if not clock.end:
                    clocks.append(
                        "- {} - haven't clocked out yet".format(
                            clock.start.strftime("%d/%m/%Y %I:%M%p")
                        )
                    )
                    difference: datetime.timedelta = (
                        datetime.datetime.now(LONDON) - clock.start
                    )
                    duration += difference
                    continue
                difference: datetime.timedelta = clock.end - clock.start
                duration += difference
                total: int = int(difference.total_seconds())
                hours, seconds = total // 3600, total % 3600
                minutes: int = seconds // 60
                parts: List[str] = []
                if hours > 0:
                    parts.append(
                        "{} hour{}".format(hours, "s" if hours > 1 else "")
                    )
                if minutes > 0:
                    parts.append(
                        "{} minute{}".format(
                            minutes, "s" if minutes > 1 else ""
                        )
                    )
                if not parts:
                    parts.append("less than a minute")
                clocks.append(
                    "- {} - {}".format(
                        clock.start.strftime("%d/%m/%Y %I:%M%p"),
                        humanize_list(parts),
                    )
                )
            total: int = int(duration.total_seconds())
            hours, seconds = total // 3600, total % 3600
            minutes: int = seconds // 60
            parts: List[str] = []
            if hours > 0:
                parts.append(
                    "{} hour{}".format(hours, "s" if hours > 1 else "")
                )
            if minutes > 0:
                parts.append(
                    "{} minute{}".format(minutes, "s" if minutes > 1 else "")
                )
            if not parts:
                parts.append("less than a minute")
            pages: List[str] = list(pagify("\n".join(clocks)))
            embeds: List[discord.Embed] = []
            async for idx, page in AsyncIter(enumerate(pages)):
                embed: discord.Embed = discord.Embed(
                    title="Time Tracker - Since {}".format(
                        datetime.datetime.fromtimestamp(
                            conf[0]["start"]
                        ).strftime("%d/%m/%Y")
                    ),
                    description=(
                        "Showing records for {}.\nTotal time - {}\n\n{}\n"
                    ).format(member.mention, humanize_list(parts), page),
                    color=await ctx.embed_color(),
                )
                embed.set_footer(text="{}/{}".format(idx + 1, len(pages)))
                embeds.append(embed)
        await SimpleMenu(embeds, disable_after_timeout=True).start(ctx)
