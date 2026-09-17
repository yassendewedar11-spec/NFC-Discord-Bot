import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import re

# =========================
# SETTINGS
# =========================

PREFIX = "!"

LOG_CHANNEL_NAME = "audit-logs"
PROMOTIONS_CHANNEL_NAME = "promotions"

STAFF_ROLE_NAMES = {
    "NFC | Managment",
    "NFC | Staff Supervisor",
    "NFC | Moderator"
}

PROMOTION_ROLES = {
    "managment": "NFC | Managment",
    "management": "NFC | Managment",
    "supervisor": "NFC | Staff Supervisor",
    "moderator": "NFC | Moderator",
    "mod": "NFC | Moderator"
}

# =========================
# BOT SETUP
# =========================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents
)

views_registered = False

# =========================
# EMBEDS
# =========================

def make_embed(title, description, emoji="📋"):
    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=description,
        color=discord.Color.blurple()
    )

    return embed


# =========================
# STAFF CHECK
# =========================

def has_staff_role(member):
    return any(
        role.name in STAFF_ROLE_NAMES
        for role in member.roles
    )


def staff_or_permission(permission_name):
    async def predicate(ctx):

        if has_staff_role(ctx.author):
            return True

        return getattr(
            ctx.author.guild_permissions,
            permission_name,
            False
        )

    return commands.check(predicate)


# =========================
# LOGGING
# =========================

async def send_log(guild, title, description, emoji="📋"):

    channel = discord.utils.get(
        guild.text_channels,
        name=LOG_CHANNEL_NAME
    )

    if not channel:
        return

    embed = make_embed(
        title,
        description,
        emoji
    )

    await channel.send(embed=embed)


# =========================
# READY
# =========================

@bot.event
async def on_ready():

    global views_registered

    if not views_registered:

        bot.add_view(TicketDashboardView())
        bot.add_view(TicketCloseView())

        views_registered = True

    synced = await bot.tree.sync()

    print(f"Bot is online as {bot.user}")
    print(f"Synced {len(synced)} slash commands.")


# =========================
# HELLO
# =========================

@bot.command()
async def hello(ctx):

    embed = make_embed(
        "Hello!",
        f"Hello {ctx.author.mention}! 👋",
        "👋"
    )

    await ctx.send(embed=embed)


@bot.tree.command(
    name="hello",
    description="Say hello"
)
async def slash_hello(interaction: discord.Interaction):

    embed = make_embed(
        "Hello!",
        f"Hello {interaction.user.mention}! 👋",
        "👋"
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
# CLEAR
# =========================

@bot.command()
@staff_or_permission("manage_messages")
async def clear(ctx, amount: int):

    if amount <= 0:
        await ctx.send("❌ Amount must be greater than 0.")
        return

    deleted = await ctx.channel.purge(
        limit=amount + 1
    )

    msg = await ctx.send(
        f"🧹 Deleted **{len(deleted) - 1}** messages."
    )

    await send_log(
        ctx.guild,
        "Messages Cleared",
        f"{ctx.author.mention} deleted **{len(deleted) - 1}** messages in {ctx.channel.mention}.",
        "🧹"
    )

    await msg.delete(delay=3)


@bot.tree.command(
    name="clear",
    description="Delete messages"
)
@app_commands.describe(
    amount="Number of messages to delete"
)
async def slash_clear(
    interaction: discord.Interaction,
    amount: int
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True
        )
        return

    if amount <= 0:
        await interaction.response.send_message(
            "❌ Amount must be greater than 0.",
            ephemeral=True
        )
        return

    await interaction.response.defer()

    deleted = await interaction.channel.purge(
        limit=amount
    )

    await interaction.followup.send(
        f"🧹 Deleted **{len(deleted)}** messages."
    )

    await send_log(
        interaction.guild,
        "Messages Cleared",
        f"{interaction.user.mention} deleted **{len(deleted)}** messages in {interaction.channel.mention}.",
        "🧹"
    )


# =========================
# KICK
# =========================

@bot.command()
@staff_or_permission("kick_members")
async def kick(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    try:

        await member.kick(reason=reason)

        embed = make_embed(
            "Member Kicked",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Reason:** {reason}",
            "👢"
        )

        await ctx.send(embed=embed)

        await send_log(
            ctx.guild,
            "Member Kicked",
            f"{member.mention} was kicked by {ctx.author.mention}.\n"
            f"Reason: {reason}",
            "👢"
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have permission to kick this member."
        )


@bot.tree.command(
    name="kick",
    description="Kick a member"
)
@app_commands.describe(
    member="Member to kick",
    reason="Reason"
)
async def slash_kick(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )
        return

    try:

        await member.kick(reason=reason)

        embed = make_embed(
            "Member Kicked",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Reason:** {reason}",
            "👢"
        )

        await interaction.response.send_message(
            embed=embed
        )

        await send_log(
            interaction.guild,
            "Member Kicked",
            f"{member.mention} was kicked by {interaction.user.mention}.\n"
            f"Reason: {reason}",
            "👢"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to kick this member.",
            ephemeral=True
        )


# =========================
# BAN
# =========================

@bot.command()
@staff_or_permission("ban_members")
async def ban(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    try:

        await member.ban(reason=reason)

        embed = make_embed(
            "Member Banned",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {ctx.author.mention}\n"
            f"**Reason:** {reason}",
            "🔨"
        )

        await ctx.send(embed=embed)

        await send_log(
            ctx.guild,
            "Member Banned",
            f"{member.mention} was banned by {ctx.author.mention}.\n"
            f"Reason: {reason}",
            "🔨"
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have permission to ban this member."
        )


@bot.tree.command(
    name="ban",
    description="Ban a member"
)
@app_commands.describe(
    member="Member to ban",
    reason="Reason"
)
async def slash_ban(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )
        return

    try:

        await member.ban(reason=reason)

        embed = make_embed(
            "Member Banned",
            f"**Member:** {member.mention}\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Reason:** {reason}",
            "🔨"
        )

        await interaction.response.send_message(
            embed=embed
        )

        await send_log(
            interaction.guild,
            "Member Banned",
            f"{member.mention} was banned by {interaction.user.mention}.\n"
            f"Reason: {reason}",
            "🔨"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission to ban this member.",
            ephemeral=True
        )


# =========================
# WARNINGS
# =========================

INFRACTIONS_FILE = "infractions.json"


def load_infractions():

    if not os.path.exists(INFRACTIONS_FILE):
        return {}

    try:

        with open(
            INFRACTIONS_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    except:

        return {}


def save_infractions(data):

    with open(
        INFRACTIONS_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4
        )


@bot.command()
@staff_or_permission("moderate_members")
async def warn(
    ctx,
    member: discord.Member,
    *,
    reason="No reason provided"
):

    data = load_infractions()

    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    if guild_id not in data:
        data[guild_id] = {}

    if user_id not in data[guild_id]:
        data[guild_id][user_id] = []

    data[guild_id][user_id].append({
        "moderator": ctx.author.id,
        "reason": reason
    })

    save_infractions(data)

    embed = make_embed(
        "Member Warned",
        f"**Member:** {member.mention}\n"
        f"**Moderator:** {ctx.author.mention}\n"
        f"**Reason:** {reason}",
        "⚠️"
    )

    await ctx.send(embed=embed)

    await send_log(
        ctx.guild,
        "Member Warned",
        f"{member.mention} was warned by {ctx.author.mention}.\n"
        f"Reason: {reason}",
        "⚠️"
    )


@bot.command()
@staff_or_permission("moderate_members")
async def warnings(
    ctx,
    member: discord.Member
):

    data = load_infractions()

    guild_id = str(ctx.guild.id)
    user_id = str(member.id)

    warnings_list = data.get(
        guild_id,
        {}
    ).get(
        user_id,
        []
    )

    if not warnings_list:

        embed = make_embed(
            "Warnings",
            f"{member.mention} has no warnings.",
            "⚠️"
        )

        await ctx.send(embed=embed)
        return

    description = ""

    for i, warning in enumerate(
        warnings_list,
        start=1
    ):

        moderator = ctx.guild.get_member(
            warning["moderator"]
        )

        moderator_text = (
            moderator.mention
            if moderator
            else "Unknown"
        )

        description += (
            f"**{i}.** {warning['reason']}\n"
            f"Moderator: {moderator_text}\n\n"
        )

    embed = make_embed(
        f"Warnings for {member}",
        description,
        "⚠️"
    )

    await ctx.send(embed=embed)


@bot.tree.command(
    name="warn",
    description="Warn a member"
)
@app_commands.describe(
    member="Member to warn",
    reason="Reason"
)
async def slash_warn(
    interaction: discord.Interaction,
    member: discord.Member,
    reason: str = "No reason provided"
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )
        return

    data = load_infractions()

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    if guild_id not in data:
        data[guild_id] = {}

    if user_id not in data[guild_id]:
        data[guild_id][user_id] = []

    data[guild_id][user_id].append({
        "moderator": interaction.user.id,
        "reason": reason
    })

    save_infractions(data)

    embed = make_embed(
        "Member Warned",
        f"**Member:** {member.mention}\n"
        f"**Moderator:** {interaction.user.mention}\n"
        f"**Reason:** {reason}",
        "⚠️"
    )

    await interaction.response.send_message(
        embed=embed
    )

    await send_log(
        interaction.guild,
        "Member Warned",
        f"{member.mention} was warned by {interaction.user.mention}.\n"
        f"Reason: {reason}",
        "⚠️"
    )


@bot.tree.command(
    name="warnings",
    description="View a member's warnings"
)
@app_commands.describe(
    member="Member"
)
async def slash_warnings(
    interaction: discord.Interaction,
    member: discord.Member
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )
        return

    data = load_infractions()

    guild_id = str(interaction.guild.id)
    user_id = str(member.id)

    warnings_list = data.get(
        guild_id,
        {}
    ).get(
        user_id,
        []
    )

    if not warnings_list:

        embed = make_embed(
            "Warnings",
            f"{member.mention} has no warnings.",
            "⚠️"
        )

        await interaction.response.send_message(
            embed=embed
        )
        return

    description = ""

    for i, warning in enumerate(
        warnings_list,
        start=1
    ):

        moderator = interaction.guild.get_member(
            warning["moderator"]
        )

        moderator_text = (
            moderator.mention
            if moderator
            else "Unknown"
        )

        description += (
            f"**{i}.** {warning['reason']}\n"
            f"Moderator: {moderator_text}\n\n"
        )

    embed = make_embed(
        f"Warnings for {member}",
        description,
        "⚠️"
    )

    await interaction.response.send_message(
        embed=embed
    )


# =========================
# TIMEOUT
# =========================

def parse_duration(duration):

    match = re.fullmatch(
        r"(\d+)(s|m|h|d)",
        duration.lower()
    )

    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2)

    if unit == "s":
        return amount

    if unit == "m":
        return amount * 60

    if unit == "h":
        return amount * 60 * 60

    if unit == "d":
        return amount * 60 * 60 * 24


@bot.command()
@staff_or_permission("moderate_members")
async def timeout(
    ctx,
    member: discord.Member,
    duration: str,
    *,
    reason="No reason provided"
):

    seconds = parse_duration(duration)

    if seconds is None:

        await ctx.send(
            "❌ Use a duration like `10m`, `2h`, or `1d`."
        )
        return

    try:

        await member.timeout(
            discord.utils.utcnow()
            + discord.timedelta(seconds=seconds),
            reason=reason
        )

    except AttributeError:

        from datetime import timedelta

        await member.timeout(
            discord.utils.utcnow()
            + timedelta(seconds=seconds),
            reason=reason
        )

    embed = make_embed(
        "Member Timed Out",
        f"**Member:** {member.mention}\n"
        f"**Duration:** {duration}\n"
        f"**Moderator:** {ctx.author.mention}\n"
        f"**Reason:** {reason}",
        "⏱️"
    )

    await ctx.send(embed=embed)

    await send_log(
        ctx.guild,
        "Member Timed Out",
        f"{member.mention} was timed out by {ctx.author.mention} for **{duration}**.\n"
        f"Reason: {reason}",
        "⏱️"
    )


@bot.command()
@staff_or_permission("moderate_members")
async def untimeout(
    ctx,
    member: discord.Member
):

    try:

        await member.timeout(
            None,
            reason=f"Removed by {ctx.author}"
        )

        embed = make_embed(
            "Timeout Removed",
            f"Timeout removed from {member.mention}.",
            "🔓"
        )

        await ctx.send(embed=embed)

        await send_log(
            ctx.guild,
            "Timeout Removed",
            f"{ctx.author.mention} removed the timeout from {member.mention}.",
            "🔓"
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I don't have permission."
        )


@bot.tree.command(
    name="timeout",
    description="Timeout a member"
)
@app_commands.describe(
    member="Member",
    duration="Example: 10m, 2h, 1d",
    reason="Reason"
)
async def slash_timeout(
    interaction: discord.Interaction,
    member: discord.Member,
    duration: str,
    reason: str = "No reason provided"
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )
        return

    seconds = parse_duration(duration)

    if seconds is None:

        await interaction.response.send_message(
            "❌ Use a duration like `10m`, `2h`, or `1d`.",
            ephemeral=True
        )
        return

    from datetime import timedelta

    try:

        await member.timeout(
            discord.utils.utcnow()
            + timedelta(seconds=seconds),
            reason=reason
        )

        embed = make_embed(
            "Member Timed Out",
            f"**Member:** {member.mention}\n"
            f"**Duration:** {duration}\n"
            f"**Moderator:** {interaction.user.mention}\n"
            f"**Reason:** {reason}",
            "⏱️"
        )

        await interaction.response.send_message(
            embed=embed
        )

        await send_log(
            interaction.guild,
            "Member Timed Out",
            f"{member.mention} was timed out by {interaction.user.mention} for **{duration}**.\n"
            f"Reason: {reason}",
            "⏱️"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission.",
            ephemeral=True
        )


@bot.tree.command(
    name="untimeout",
    description="Remove a member's timeout"
)
@app_commands.describe(
    member="Member"
)
async def slash_untimeout(
    interaction: discord.Interaction,
    member: discord.Member
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )
        return

    try:

        await member.timeout(
            None,
            reason=f"Removed by {interaction.user}"
        )

        embed = make_embed(
            "Timeout Removed",
            f"Timeout removed from {member.mention}.",
            "🔓"
        )

        await interaction.response.send_message(
            embed=embed
        )

        await send_log(
            interaction.guild,
            "Timeout Removed",
            f"{interaction.user.mention} removed the timeout from {member.mention}.",
            "🔓"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I don't have permission.",
            ephemeral=True
        )


# ==================================================
# TICKETS
# ==================================================

class TicketCloseView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=discord.ButtonStyle.red,
        custom_id="ticket_close"
    )
    async def close_ticket(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        channel = interaction.channel

        if not channel.name.startswith("ticket-"):

            await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True
            )

            return

        if not has_staff_role(interaction.user):

            parts = channel.name.split("-")

            if len(parts) != 3:

                await interaction.response.send_message(
                    "❌ Invalid ticket.",
                    ephemeral=True
                )

                return

            try:

                owner_id = int(parts[2])

            except ValueError:

                await interaction.response.send_message(
                    "❌ Invalid ticket.",
                    ephemeral=True
                )

                return

            if interaction.user.id != owner_id:

                await interaction.response.send_message(
                    "❌ Only the ticket owner or staff can close this ticket.",
                    ephemeral=True
                )

                return

        await interaction.response.send_message(
            "🔒 Closing ticket...",
            ephemeral=True
        )

        await send_log(
            interaction.guild,
            "Ticket Closed",
            f"**Channel:** {channel.name}\n"
            f"**Closed by:** {interaction.user.mention}",
            "🔒"
        )

        await channel.delete(
            reason=f"Ticket closed by {interaction.user}"
        )


class TicketDashboardView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=None
        )

    async def create_ticket(
        self,
        interaction,
        ticket_type
    ):

        guild = interaction.guild
        member = interaction.user

        channel_name = (
            f"ticket-{ticket_type}-{member.id}"
        )

        existing = discord.utils.get(
            guild.text_channels,
            name=channel_name
        )

        if existing:

            await interaction.response.send_message(
                f"❌ You already have a {ticket_type} ticket: {existing.mention}",
                ephemeral=True
            )

            return

        overwrites = {

            guild.default_role:
                discord.PermissionOverwrite(
                    view_channel=False
                ),

            member:
                discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )
        }

        for role in guild.roles:

            if role.name in STAFF_ROLE_NAMES:

                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True
                )

        channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites
        )

        titles = {

            "partner":
                "🤝 Partnership Ticket",

            "apply":
                "📝 Application Ticket",

            "report":
                "🚨 Report Ticket"
        }

        descriptions = {

            "partner":
                "Please provide the details of your partnership request.",

            "apply":
                "Please provide the information needed for your staff application.",

            "report":
                "Please explain the issue or report in as much detail as possible."
        }

        embed = make_embed(
            titles[ticket_type],

            f"Welcome {member.mention}!\n\n"
            f"{descriptions[ticket_type]}\n\n"
            "A staff member will assist you shortly.",
            "🎫"
        )

        await channel.send(
            content=member.mention,
            embed=embed,
            view=TicketCloseView()
        )

        await interaction.response.send_message(
            f"✅ Your {ticket_type} ticket has been created: {channel.mention}",
            ephemeral=True
        )

        await send_log(
            guild,
            "Ticket Created",
            f"{member.mention} created a **{ticket_type}** ticket: {channel.mention}",
            "🎫"
        )

    @discord.ui.button(
        label="Partner",
        emoji="🤝",
        style=discord.ButtonStyle.blurple,
        custom_id="ticket_partner"
    )
    async def partner(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.create_ticket(
            interaction,
            "partner"
        )

    @discord.ui.button(
        label="Apply",
        emoji="📝",
        style=discord.ButtonStyle.green,
        custom_id="ticket_apply"
    )
    async def apply(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.create_ticket(
            interaction,
            "apply"
        )

    @discord.ui.button(
        label="Report",
        emoji="🚨",
        style=discord.ButtonStyle.red,
        custom_id="ticket_report"
    )
    async def report(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await self.create_ticket(
            interaction,
            "report"
        )


# =========================
# TICKET DASHBOARD
# =========================

@bot.command()
@staff_or_permission("manage_channels")
async def ticket_dashboard(ctx):

    embed = make_embed(
        "NFC Ticket Center",

        "Choose the type of ticket you want to open.\n\n"

        "🤝 **Partner** — Partnership requests\n"
        "📝 **Apply** — Staff applications\n"
        "🚨 **Report** — Report an issue or member\n\n"

        "A private ticket will be created for you.",

        "🎫"
    )

    await ctx.send(
        embed=embed,
        view=TicketDashboardView()
    )


@bot.tree.command(
    name="ticket-dashboard",
    description="Send the NFC ticket dashboard"
)
async def slash_ticket_dashboard(
    interaction: discord.Interaction
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.manage_channels:

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    embed = make_embed(
        "NFC Ticket Center",

        "Choose the type of ticket you want to open.\n\n"

        "🤝 **Partner** — Partnership requests\n"
        "📝 **Apply** — Staff applications\n"
        "🚨 **Report** — Report an issue or member\n\n"

        "A private ticket will be created for you.",

        "🎫"
    )

    await interaction.response.send_message(
        embed=embed,
        view=TicketDashboardView()
    )


# =========================
# OLD SIMPLE TICKET
# =========================

@bot.command()
async def ticket(ctx):

    await TicketDashboardView().create_ticket(
        FakeInteraction(ctx),
        "report"
    )


# =========================
# CLOSE COMMAND
# =========================

@bot.command()
@staff_or_permission("manage_channels")
async def close(ctx):

    if not ctx.channel.name.startswith("ticket-"):

        await ctx.send(
            "❌ This is not a ticket channel."
        )

        return

    await send_log(
        ctx.guild,
        "Ticket Closed",
        f"**Channel:** {ctx.channel.name}\n"
        f"**Closed by:** {ctx.author.mention}",
        "🔒"
    )

    await ctx.send(
        "🔒 Closing ticket..."
    )

    await ctx.channel.delete(
        reason=f"Ticket closed by {ctx.author}"
    )


@bot.tree.command(
    name="close",
    description="Close the current ticket"
)
async def slash_close(
    interaction: discord.Interaction
):

    if not interaction.channel.name.startswith("ticket-"):

        await interaction.response.send_message(
            "❌ This is not a ticket channel.",
            ephemeral=True
        )

        return

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.manage_channels:

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    await interaction.response.send_message(
        "🔒 Closing ticket..."
    )

    await send_log(
        interaction.guild,
        "Ticket Closed",
        f"**Channel:** {interaction.channel.name}\n"
        f"**Closed by:** {interaction.user.mention}",
        "🔒"
    )

    await interaction.channel.delete(
        reason=f"Ticket closed by {interaction.user}"
    )


# =========================
# PROMOTIONS
# =========================

@bot.command()
@staff_or_permission("manage_roles")
async def promote(
    ctx,
    member: discord.Member,
    role_name: str,
    *,
    reason="No reason provided"
):

    key = role_name.lower()

    if key not in PROMOTION_ROLES:

        await ctx.send(
            "❌ Invalid role.\n"
            "Use: `Managment`, `Supervisor`, or `Moderator`."
        )

        return

    role = discord.utils.get(
        ctx.guild.roles,
        name=PROMOTION_ROLES[key]
    )

    if not role:

        await ctx.send(
            "❌ That role doesn't exist."
        )

        return

    try:

        await member.add_roles(role)

        embed = make_embed(
            "Promotion",
            f"🎉 {member.mention} has been promoted!\n\n"
            f"**New Role:** {role.mention}\n"
            f"**Promoted by:** {ctx.author.mention}\n"
            f"**Reason:** {reason}",
            "📈"
        )

        promotions = discord.utils.get(
            ctx.guild.text_channels,
            name=PROMOTIONS_CHANNEL_NAME
        )

        if promotions:

            await promotions.send(
                embed=embed
            )

        await send_log(
            ctx.guild,
            "Promotion",
            f"{member.mention} was promoted to {role.name} by {ctx.author.mention}.\n"
            f"Reason: {reason}",
            "📈"
        )

        await ctx.send(
            embed=embed
        )

    except discord.Forbidden:

        await ctx.send(
            "❌ I can't give that role. Make sure my bot role is above the promotion roles."
        )


@bot.tree.command(
    name="promote",
    description="Promote a member"
)
@app_commands.describe(
    member="Member to promote",
    role="Role to give",
    reason="Reason"
)
@app_commands.choices(
    role=[
        app_commands.Choice(
            name="NFC | Managment",
            value="managment"
        ),

        app_commands.Choice(
            name="NFC | Staff Supervisor",
            value="supervisor"
        ),

        app_commands.Choice(
            name="NFC | Moderator",
            value="moderator"
        )
    ]
)
async def slash_promote(
    interaction: discord.Interaction,
    member: discord.Member,
    role: app_commands.Choice[str],
    reason: str = "No reason provided"
):

    if not has_staff_role(interaction.user) and not interaction.user.guild_permissions.manage_roles:

        await interaction.response.send_message(
            "❌ You don't have permission.",
            ephemeral=True
        )

        return

    role_name = PROMOTION_ROLES[role.value]

    discord_role = discord.utils.get(
        interaction.guild.roles,
        name=role_name
    )

    if not discord_role:

        await interaction.response.send_message(
            "❌ That role doesn't exist.",
            ephemeral=True
        )

        return

    try:

        await member.add_roles(
            discord_role
        )

        embed = make_embed(
            "Promotion",
            f"🎉 {member.mention} has been promoted!\n\n"
            f"**New Role:** {discord_role.mention}\n"
            f"**Promoted by:** {interaction.user.mention}\n"
            f"**Reason:** {reason}",
            "📈"
        )

        promotions = discord.utils.get(
            interaction.guild.text_channels,
            name=PROMOTIONS_CHANNEL_NAME
        )

        if promotions:

            await promotions.send(
                embed=embed
            )

        await interaction.response.send_message(
            embed=embed
        )

        await send_log(
            interaction.guild,
            "Promotion",
            f"{member.mention} was promoted to {discord_role.name} by {interaction.user.mention}.\n"
            f"Reason: {reason}",
            "📈"
        )

    except discord.Forbidden:

        await interaction.response.send_message(
            "❌ I can't give that role. Make sure my bot role is above the promotion roles.",
            ephemeral=True
        )


# =========================
# ERROR HANDLER
# =========================

@bot.event
async def on_command_error(
    ctx,
    error
):

    if isinstance(
        error,
        commands.CheckFailure
    ):

        await ctx.send(
            "❌ You don't have permission to use this command."
        )

        return

    if isinstance(
        error,
        commands.MissingRequiredArgument
    ):

        await ctx.send(
            "❌ You're missing an argument."
        )

        return

    if isinstance(
        error,
        commands.BadArgument
    ):

        await ctx.send(
            "❌ Invalid member or argument."
        )

        return

    print(
        f"Command error: {error}"
    )
