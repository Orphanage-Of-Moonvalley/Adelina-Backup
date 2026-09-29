# ============================================================
# IMPORTS
# ============================================================
import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import sqlite3
import time
import os
from flask import Flask
import threading

# ============================================================
# CONFIGURATION
# ============================================================
GUILD_ID = 1484933010041213091

WARN_LOG_CHANNEL = 1551376218501287937
BAN_LOG_CHANNEL = 1551376272125337600
ERROR_LOG_CHANNEL = 1551376368971939900

HR_ROLE = 1549971988846612560
SHR_ROLE = 1549973508661059675
SECRETARY_ROLE = 1549558292714364948
MOTHER_ADELINÈ_ROLE = 1543075528624312411

SERVER_NAME = "Lé Sancturaré Adelinè"
BOT_NAME = "Adelina"
APPEAL_LINK = "https://discord.gg/9Q9mPwD5xJ"

DB_PATH = "warnings.db"

# ============================================================
# KEEP-ALIVE WEBSITE (Render requirement)
# ============================================================
app = Flask(__name__)

@app.route("/")
def home():
    return "Ready to monitor the community!"

def run_web():
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web, daemon=True).start()

# ============================================================
# DISCORD INTENTS & BOT SETUP
# ============================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

start_time = datetime.datetime.now(datetime.UTC)

# ============================================================
# SQLITE DATABASE SETUP
# ============================================================
def db_connect():
    return sqlite3.connect(DB_PATH)

def init_database():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id TEXT,
            reason TEXT,
            timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()

def init_moderation_log():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS moderation_log (
            user_id TEXT,
            staff_id TEXT,
            action TEXT,
            reason TEXT,
            timestamp INTEGER
        )
    """)
    conn.commit()
    conn.close()

# Initialize both tables
init_database()
init_moderation_log()

# ============================================================
# WARNING SYSTEM FUNCTIONS
# ============================================================
def add_warning(user_id, reason):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO warnings (user_id, reason, timestamp) VALUES (?, ?, ?)",
        (str(user_id), reason, int(time.time()))
    )
    conn.commit()
    conn.close()

def remove_one_warning(user_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT rowid FROM warnings WHERE user_id = ? ORDER BY timestamp ASC",
        (str(user_id),)
    )
    rows = cursor.fetchall()
    if rows:
        cursor.execute("DELETE FROM warnings WHERE rowid = ?", (rows[0][0],))
        conn.commit()
    conn.close()

def count_warnings(user_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM warnings WHERE user_id = ?", (str(user_id),))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_warnings(user_id):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT reason, timestamp FROM warnings WHERE user_id = ? ORDER BY timestamp ASC",
        (str(user_id),)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_all_users_with_warnings():
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user_id FROM warnings")
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

# ============================================================
# MODERATION LOG FUNCTIONS
# ============================================================
def log_action(user_id, staff_id, action, reason):
    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO moderation_log (user_id, staff_id, action, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
        (str(user_id), str(staff_id), action, reason, int(time.time()))
    )
    conn.commit()
    conn.close()

# ============================================================
# AUTO CLEANUP (30 DAYS)
# ============================================================
@tasks.loop(minutes=1)
async def cleanup_old_warnings():
    conn = db_connect()
    cursor = conn.cursor()
    cutoff = int(time.time()) - (30 * 24 * 60 * 60)  # 30 days
    cursor.execute("DELETE FROM warnings WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()

@tasks.loop(minutes=1)
async def cleanup_old_history():
    conn = db_connect()
    cursor = conn.cursor()
    cutoff = int(time.time()) - (30 * 24 * 60 * 60)  # 30 days
    cursor.execute("DELETE FROM moderation_log WHERE timestamp < ?", (cutoff,))
    conn.commit()
    conn.close()

# ============================================================
# ROLE CHECKING
# ============================================================
def has_role(member: discord.Member, role_id: int):
    return discord.utils.get(member.roles, id=role_id) is not None

def can_warn(member: discord.Member):
    # HR, SHR, Secretary, Mother Adelinè CAN issue warnings
    return (
        has_role(member, HR_ROLE) or
        has_role(member, SHR_ROLE) or
        has_role(member, SECRETARY_ROLE) or
        has_role(member, MOTHER_ADELINÈ_ROLE)
    )

def can_ban(member: discord.Member):
    # SHR, Secretary, Mother Adelinè CAN ban
    return (
        has_role(member, SHR_ROLE) or
        has_role(member, SECRETARY_ROLE) or
        has_role(member, MOTHER_ADELINÈ_ROLE)
    )

def can_announce(member: discord.Member):
    # Secretary + Mother Adelinè CAN announce
    return (
        has_role(member, SECRETARY_ROLE) or
        has_role(member, MOTHER_ADELINÈ_ROLE)
    )

def get_staff_rank(member: discord.Member):
    if has_role(member, SHR_ROLE): return "SHR"
    if has_role(member, HR_ROLE): return "HR"
    if has_role(member, SECRETARY_ROLE): return "Secretary"
    if has_role(member, MOTHER_ADELINÈ_ROLE): return "Mother Adelinè"
    return "Staff"

# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Prevent commands from being used in DMs
async def deny_dm(interaction: discord.Interaction):
    if isinstance(interaction.channel, discord.DMChannel):
        await interaction.response.send_message(
            "❌ Commands cannot be used in DMs.",
            ephemeral=True
        )
        return True
    return False

# Version system (used for update notifications)
def get_version():
    try:
        with open("version.txt", "r") as f:
            return f.read().strip()
    except:
        return "unknown"

# ============================================================
# ON READY EVENT
# ============================================================

@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)

    if guild:
        # Sync guild-specific commands
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} commands to {guild.name}.")

    # Start cleanup tasks only once
    if not cleanup_old_warnings.is_running():
        cleanup_old_warnings.start()

    if not cleanup_old_history.is_running():
        cleanup_old_history.start()

    # Send update notification
    version = get_version()
    log_channel = bot.get_channel(ERROR_LOG_CHANNEL)

    if log_channel:
        try:
            await log_channel.send(
                f"🆕 **Adelina has been updated.**\n"
                f"Current version: `{version}`"
            )
        except Exception:
            pass

    # Set presence
    await bot.change_presence(
        activity=discord.Game("⚖️ Monitoring the community server.")
    )

    print(
        f"{BOT_NAME} is online as {bot.user} in "
        f"{guild.name if guild else 'Unknown Guild'}."
    )

# ============================================================
# /WARN COMMAND
# ============================================================
@tree.command(name="warn", description="Warn a user.")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):

    if await deny_dm(interaction):
        return

    if not can_warn(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    # Prevent self-warning
    if interaction.user.id == member.id:
        return await interaction.response.send_message(
            "❌ You cannot warn yourself.",
            ephemeral=True
        )

    # Prevent warning Adelina
    if member.id == bot.user.id:
        return await interaction.response.send_message(
            "❌ You cannot warn Adelina.",
            ephemeral=True
        )

    # Prevent warning Secretary
    if has_role(member, SECRETARY_ROLE):
        return await interaction.response.send_message(
            "❌ You cannot warn a Secretary.",
            ephemeral=True
        )

    # Prevent warning Mother Adelinè
    if has_role(member, MOTHER_ADELINÈ_ROLE):
        return await interaction.response.send_message(
            "❌ You cannot warn a Mother Adelinè.",
            ephemeral=True
        )

    # Prevent warning SHR
    if has_role(member, SHR_ROLE):
        return await interaction.response.send_message(
            "❌ You cannot warn an SHR.",
            ephemeral=True
        )

    # Normal warning logic
    add_warning(member.id, reason)
    count = count_warnings(member.id)
    log_action(member.id, interaction.user.id, "warn", reason)

    rank = get_staff_rank(interaction.user)

    embed = discord.Embed(
        title=f"⚠️ You have been warned at {SERVER_NAME}.",
        color=0xFFCC00
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Warnings", value=f"{count}/3", inline=False)
    embed.add_field(name="Appeal", value=APPEAL_LINK, inline=False)
    embed.add_field(name="Warning issued by", value=rank, inline=False)

    try:
        await member.send(embed=embed)
    except:
        pass

    log_channel = interaction.guild.get_channel(WARN_LOG_CHANNEL)
    if log_channel:
        log_embed = discord.Embed(
            title="⚠️ Someone received a warning.",
            color=0xFFCC00
        )
        log_embed.add_field(name="Warning issued by", value=interaction.user.mention, inline=False)
        log_embed.add_field(name="Person who received the warning", value=member.mention, inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.add_field(
            name="Time",
            value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inline=False
        )
        await log_channel.send(embed=log_embed)

    await interaction.response.send_message(
        f"{member.mention} has been warned ({count}/3).",
        ephemeral=True
    )

# ============================================================
# /UNWARN COMMAND
# ============================================================
@tree.command(name="unwarn", description="Remove one warning.")
async def unwarn(interaction: discord.Interaction, member: discord.Member):

    if await deny_dm(interaction):
        return

    if not can_warn(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    # Prevent self-unwarn
    if interaction.user.id == member.id:
        return await interaction.response.send_message(
            "❌ You cannot unwarn yourself.",
            ephemeral=True
        )

    if count_warnings(member.id) == 0:
        return await interaction.response.send_message(
            f"{member.mention} has no warnings.",
            ephemeral=True
        )

    remove_one_warning(member.id)
    count = count_warnings(member.id)
    log_action(member.id, interaction.user.id, "unwarn", "Removed one warning")

    embed = discord.Embed(
        title=f"✅ One of your warnings has been removed at {SERVER_NAME}.",
        color=0x57F287
    )
    embed.add_field(name="You now have", value=f"{count}/3 warnings.", inline=False)

    try:
        await member.send(embed=embed)
    except:
        pass

    await interaction.response.send_message(
        f"Removed one warning from {member.mention}. ({count}/3)",
        ephemeral=True
    )

# ============================================================
# /WARNINGS (SHR ONLY)
# ============================================================
@tree.command(name="warnings", description="Show all users with active warnings.")
async def warnings_cmd(interaction: discord.Interaction):

    if await deny_dm(interaction):
        return

    if not has_role(interaction.user, SHR_ROLE):
        return await interaction.response.send_message(
            "❌ Only SHR can view all warnings.",
            ephemeral=True
        )

    users = get_all_users_with_warnings()

    if not users:
        return await interaction.response.send_message(
            "There are **no active warnings**.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"⚠️ Active Warnings — {SERVER_NAME}",
        color=0xFFCC00
    )

    for user_id in users:
        warnings_list = get_all_warnings(user_id)
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else f"User ID {user_id}"

        value_text = ""

        for index, (reason, timestamp) in enumerate(warnings_list, start=1):
            warn_date = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            expires_at = timestamp + (30 * 24 * 60 * 60)
            remaining = expires_at - int(time.time())

            if remaining > 0:
                expires_text = f"{remaining // 86400} days left"
            else:
                expires_text = "Expired (auto-remove soon)"

            value_text += (
                f"**Warning {index}:** {reason}\n"
                f"• Date: {warn_date}\n"
                f"• Expires: {expires_text}\n\n"
            )

        embed.add_field(name=name, value=value_text, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================
# /BAN COMMAND
# ============================================================
@tree.command(name="ban", description="Ban a user.")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str):

    if await deny_dm(interaction):
        return

    if not can_ban(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    # DM to banned user
    try:
        await member.send(
            f"⛔ You have been banned from {SERVER_NAME}.\nReason: {reason}\nAppeal: {APPEAL_LINK}"
        )
    except:
        pass

    # Ban the user
    await member.ban(reason=reason)

    # Log action
    log_action(member.id, interaction.user.id, "ban", reason)

    # Log embed
    log_channel = interaction.guild.get_channel(BAN_LOG_CHANNEL)
    if log_channel:
        log_embed = discord.Embed(
            title="⛔ Someone got banned.",
            color=0xFF0000
        )
        log_embed.add_field(name="Banned by", value=interaction.user.mention, inline=False)
        log_embed.add_field(name="Person banned", value=member.mention, inline=False)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        log_embed.add_field(
            name="Time",
            value=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            inline=False
        )
        await log_channel.send(embed=log_embed)

    await interaction.response.send_message(
        f"{member.mention} has been banned.",
        ephemeral=True
    )

# ============================================================
# /HISTORY (SHR ONLY)
# ============================================================
@tree.command(name="history", description="Show full moderation history of all users.")
async def history(interaction: discord.Interaction):

    if await deny_dm(interaction):
        return

    if not has_role(interaction.user, SHR_ROLE):
        return await interaction.response.send_message(
            "❌ Only SHR can view the full moderation history.",
            ephemeral=True
        )

    conn = db_connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, staff_id, action, reason, timestamp FROM moderation_log ORDER BY timestamp DESC"
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        return await interaction.response.send_message(
            "There are **no moderation logs**.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"📜 Full Moderation History — {SERVER_NAME}",
        color=0x2b2d31
    )

    for user_id, staff_id, action, reason, timestamp in rows:
        member = interaction.guild.get_member(int(user_id))
        user_name = member.display_name if member else f"User ID {user_id}"

        staff_member = interaction.guild.get_member(int(staff_id))
        staff_name = staff_member.display_name if staff_member else f"Staff ID {staff_id}"

        date = datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")

        embed.add_field(
            name=f"{action.upper()} — {date}",
            value=f"**User:** {user_name}\n**Reason:** {reason}\n**Staff:** {staff_name}",
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================
# USER SELECT MENU FOR ANNOUNCE
# ============================================================
class UserSelect(discord.ui.UserSelect):
    def __init__(self, message, channel, embed_mode):
        super().__init__(placeholder="Select a user to ping...", min_values=1, max_values=1)
        self.message = message
        self.channel = channel
        self.embed_mode = embed_mode

    async def callback(self, interaction: discord.Interaction):
        selected_user = self.values[0]

        if self.embed_mode:
            embed = discord.Embed(
                title=f"📢 Announcement — {SERVER_NAME}",
                description=self.message,
                color=0x5865F2
            )
            await self.channel.send(content=selected_user.mention, embed=embed)
        else:
            await self.channel.send(f"{selected_user.mention} {self.message}")

        await interaction.response.send_message("Announcement sent.", ephemeral=True)


class PingSelect(discord.ui.Select):
    def __init__(self, message, channel, embed_mode):
        self.message = message
        self.channel = channel
        self.embed_mode = embed_mode

        options = [
            discord.SelectOption(label="None", value="none"),
            discord.SelectOption(label="@everyone", value="everyone"),
            discord.SelectOption(label="@here", value="here"),
            discord.SelectOption(label="Ping a User", value="user"),
        ]

        super().__init__(placeholder="Choose ping type...", options=options)

    async def callback(self, interaction: discord.Interaction):

        ping = self.values[0]

        # No ping
        if ping == "none":
            if self.embed_mode:
                embed = discord.Embed(
                    title=f"📢 Announcement — {SERVER_NAME}",
                    description=self.message,
                    color=0x5865F2
                )
                await self.channel.send(embed=embed)
            else:
                await self.channel.send(self.message)

            return await interaction.response.send_message("Announcement sent.", ephemeral=True)

        # @everyone
        if ping == "everyone":
            if self.embed_mode:
                embed = discord.Embed(
                    title=f"📢 Announcement — {SERVER_NAME}",
                    description=self.message,
                    color=0x5865F2
                )
                await self.channel.send(content="@everyone", embed=embed)
            else:
                await self.channel.send(f"@everyone {self.message}")

            return await interaction.response.send_message("Announcement sent.", ephemeral=True)

        # @here
        if ping == "here":
            if self.embed_mode:
                embed = discord.Embed(
                    title=f"📢 Announcement — {SERVER_NAME}",
                    description=self.message,
                    color=0x5865F2
                )
                await self.channel.send(content="@here", embed=embed)
            else:
                await self.channel.send(f"@here {self.message}")

            return await interaction.response.send_message("Announcement sent.", ephemeral=True)

        # Ping a specific user
        if ping == "user":
            view = discord.ui.View(timeout=60)
            view.add_item(UserSelect(self.message, self.channel, self.embed_mode))
            return await interaction.response.send_message(
                "Select a user to ping:",
                view=view,
                ephemeral=True
            )


class PingView(discord.ui.View):
    def __init__(self, message, channel, embed_mode):
        super().__init__(timeout=60)
        self.add_item(PingSelect(message, channel, embed_mode))

# ============================================================
# /ANNOUNCE (with embed)
# ============================================================
@tree.command(name="announce", description="Send an announcement with an embed.")
async def announce(interaction: discord.Interaction, message: str, channel: discord.TextChannel):

    if await deny_dm(interaction):
        return

    if not can_announce(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    view = PingView(message, channel, True)
    await interaction.response.send_message("Select ping type:", view=view, ephemeral=True)

# ============================================================
# /ANNOUNCE_TEXT (without embed)
# ============================================================
@tree.command(name="announce_text", description="Send an announcement without an embed.")
async def announce_text(interaction: discord.Interaction, message: str, channel: discord.TextChannel):

    if await deny_dm(interaction):
        return

    if not can_announce(interaction.user):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    view = PingView(message, channel, False)
    await interaction.response.send_message("Select ping type:", view=view, ephemeral=True)

# ============================================================
# /DASHBOARD
# ============================================================
@tree.command(name="dashboard", description="Shows moderation tools.")
async def dashboard(interaction: discord.Interaction):

    if await deny_dm(interaction):
        return

    embed = discord.Embed(
        title=f"🛠️ Moderation Dashboard — {SERVER_NAME}",
        description=(
            "**HR:** /warn, /unwarn\n"
            "**SHR:** /warn, /unwarn, /ban, /warnings, /history\n"
            "**Secretary / Mother Adelinè:** /warn, /unwarn, /ban, /announce, /announce_text\n"
            "**Everyone:** /logs"
        ),
        color=0x2b2d31
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================================
# BOT START
# ============================================================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    print("❌ ERROR: No TOKEN found in environment variables.")
else:
    bot.run(TOKEN)
