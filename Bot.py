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
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURATION
# ============================================================

GUILD_ID = 1484933010041213091

WARN_LOG_CHANNEL = 1551376218501287937
BAN_LOG_CHANNEL = 1551376272125337600
ERROR_LOG_CHANNEL = 1551376368971939900

INACTIVITY_LOG_CHANNEL = 1551338468901265458
INACTIVITY_ROLE = 1554582113427128401

HR_ROLE = 1549971988846612560
SHR_ROLE = 1549973508661059675
SECRETARY_ROLE = 1549558292714364948
MOTHER_ADELINÈ_ROLE = 1543075528624312411

SERVER_NAME = "Lé Sancturaré Adelinè"
BOT_NAME = "Adelina"

APPEAL_LINK = "https://discord.gg/9Q9mPwD5xJ"

DB_PATH = "warnings.db"

GERMANY_TZ = ZoneInfo("Europe/Berlin")

INACTIVITY_COOLDOWN_DAYS = 14


# ============================================================
# KEEP-ALIVE WEBSITE
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

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)

tree = bot.tree

start_time = datetime.datetime.now(datetime.UTC)


# ============================================================
# DATABASE
# ============================================================

def db_connect():
    return sqlite3.connect(DB_PATH)


def init_database():

    conn = db_connect()
    cursor = conn.cursor()

    # Warnings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warnings (
            user_id TEXT,
            reason TEXT,
            timestamp INTEGER
        )
    """)

    # Inactivity
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inactivity (
            user_id TEXT PRIMARY KEY,
            rank TEXT NOT NULL,
            reason TEXT NOT NULL,
            start_timestamp INTEGER NOT NULL,
            end_timestamp INTEGER NOT NULL,
            emergency INTEGER NOT NULL DEFAULT 0,
            ended_timestamp INTEGER
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


init_database()
init_moderation_log()


# ============================================================
# WARNING SYSTEM
# ============================================================

def add_warning(user_id, reason):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO warnings
        (user_id, reason, timestamp)
        VALUES (?, ?, ?)
        """,
        (
            str(user_id),
            reason,
            int(time.time())
        )
    )

    conn.commit()
    conn.close()


def remove_one_warning(user_id):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT rowid
        FROM warnings
        WHERE user_id = ?
        ORDER BY timestamp ASC
        """,
        (str(user_id),)
    )

    rows = cursor.fetchall()

    if rows:

        cursor.execute(
            "DELETE FROM warnings WHERE rowid = ?",
            (rows[0][0],)
        )

        conn.commit()

    conn.close()


def count_warnings(user_id):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM warnings WHERE user_id = ?",
        (str(user_id),)
    )

    count = cursor.fetchone()[0]

    conn.close()

    return count


def get_all_warnings(user_id):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT reason, timestamp
        FROM warnings
        WHERE user_id = ?
        ORDER BY timestamp ASC
        """,
        (str(user_id),)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_all_users_with_warnings():

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT user_id FROM warnings"
    )

    rows = cursor.fetchall()

    conn.close()

    return [row[0] for row in rows]


# ============================================================
# MODERATION LOG
# ============================================================

def log_action(user_id, staff_id, action, reason):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO moderation_log
        (user_id, staff_id, action, reason, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            str(user_id),
            str(staff_id),
            action,
            reason,
            int(time.time())
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# INACTIVITY DATABASE
# ============================================================

def add_inactivity(
    user_id,
    rank,
    reason,
    start_timestamp,
    end_timestamp,
    emergency
):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO inactivity
        (
            user_id,
            rank,
            reason,
            start_timestamp,
            end_timestamp,
            emergency,
            ended_timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            str(user_id),
            rank,
            reason,
            start_timestamp,
            end_timestamp,
            int(emergency)
        )
    )

    conn.commit()
    conn.close()


def get_inactivity(user_id):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            rank,
            reason,
            start_timestamp,
            end_timestamp,
            emergency,
            ended_timestamp
        FROM inactivity
        WHERE user_id = ?
        """,
        (str(user_id),)
    )

    row = cursor.fetchone()

    conn.close()

    return row


def get_active_inactivities():

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            rank,
            reason,
            start_timestamp,
            end_timestamp,
            emergency
        FROM inactivity
        WHERE ended_timestamp IS NULL
        ORDER BY end_timestamp ASC
        """
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_last_ended_inactivity(user_id):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT ended_timestamp
        FROM inactivity
        WHERE user_id = ?
        AND ended_timestamp IS NOT NULL
        ORDER BY ended_timestamp DESC
        LIMIT 1
        """,
        (str(user_id),)
    )

    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]

    return None


def finish_inactivity(user_id):

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE inactivity
        SET ended_timestamp = ?
        WHERE user_id = ?
        AND ended_timestamp IS NULL
        """,
        (
            int(time.time()),
            str(user_id)
        )
    )

    conn.commit()
    conn.close()


# ============================================================
# AUTO CLEANUP
# ============================================================

@tasks.loop(minutes=1)
async def cleanup_old_warnings():

    conn = db_connect()
    cursor = conn.cursor()

    cutoff = int(time.time()) - (
        30 * 24 * 60 * 60
    )

    cursor.execute(
        "DELETE FROM warnings WHERE timestamp < ?",
        (cutoff,)
    )

    conn.commit()
    conn.close()


@tasks.loop(minutes=1)
async def cleanup_old_history():

    conn = db_connect()
    cursor = conn.cursor()

    cutoff = int(time.time()) - (
        30 * 24 * 60 * 60
    )

    cursor.execute(
        "DELETE FROM moderation_log WHERE timestamp < ?",
        (cutoff,)
    )

    conn.commit()
    conn.close()


# ============================================================
# AUTOMATIC INACTIVITY END
# ============================================================

@tasks.loop(minutes=1)
async def process_inactivities():

    now = datetime.datetime.now(GERMANY_TZ)
    now_timestamp = int(now.timestamp())

    rows = get_active_inactivities()

    guild = bot.get_guild(GUILD_ID)

    if not guild:
        return

    for (
        user_id,
        rank,
        reason,
        start_timestamp,
        end_timestamp,
        emergency
    ) in rows:

        if now_timestamp < end_timestamp:
            continue

        member = guild.get_member(int(user_id))

        # Mark as finished
        finish_inactivity(user_id)

        # Remove inactivity role
        if member:

            role = guild.get_role(INACTIVITY_ROLE)

            if role and role in member.roles:

                try:

                    await member.remove_roles(
                        role,
                        reason="Inactivity notice ended."
                    )

                except discord.Forbidden:
                    pass

        # Send welcome-back message
        channel = guild.get_channel(
            INACTIVITY_LOG_CHANNEL
        )

        if channel:

            if member:
                user_text = member.mention
            else:
                user_text = f"<@{user_id}>"

            embed = discord.Embed(
                description=(
                    f"Greetings, {user_text}! "
                    "Your inactivity notice has ended today, "
                    "welcome back!\n\n"
                    "For any questions or concerns feel free "
                    "to ask an HR+."
                ),
                color=0x57F287
            )

            await channel.send(embed=embed)


# ============================================================
# ROLE CHECKING
# ============================================================

def has_role(member: discord.Member, role_id: int):

    return discord.utils.get(
        member.roles,
        id=role_id
    ) is not None


def can_warn(member: discord.Member):

    return (
        has_role(member, HR_ROLE)
        or has_role(member, SHR_ROLE)
        or has_role(member, SECRETARY_ROLE)
        or has_role(member, MOTHER_ADELINÈ_ROLE)
    )


def can_ban(member: discord.Member):

    return (
        has_role(member, SHR_ROLE)
        or has_role(member, SECRETARY_ROLE)
        or has_role(member, MOTHER_ADELINÈ_ROLE)
    )


def can_announce(member: discord.Member):

    return (
        has_role(member, SECRETARY_ROLE)
        or has_role(member, MOTHER_ADELINÈ_ROLE)
    )


def can_inactivity(member: discord.Member):

    return (
        has_role(member, HR_ROLE)
        or has_role(member, SHR_ROLE)
        or has_role(member, SECRETARY_ROLE)
        or has_role(member, MOTHER_ADELINÈ_ROLE)
    )


def get_staff_rank(member: discord.Member):

    if has_role(member, SHR_ROLE):
        return "SHR"

    if has_role(member, HR_ROLE):
        return "HR"

    if has_role(member, SECRETARY_ROLE):
        return "Secretary"

    if has_role(member, MOTHER_ADELINÈ_ROLE):
        return "Mother Adelinè"

    return "Staff"


# ============================================================
# HELPERS
# ============================================================

async def deny_dm(interaction: discord.Interaction):

    if isinstance(
        interaction.channel,
        discord.DMChannel
    ):

        await interaction.response.send_message(
            "❌ Commands cannot be used in DMs.",
            ephemeral=True
        )

        return True

    return False


def get_version():

    try:

        with open("version.txt", "r") as f:
            return f.read().strip()

    except:

        return "unknown"


# ============================================================
# INACTIVITY UI
# ============================================================

def parse_inactivity_duration(duration_text):

    duration = duration_text.strip().lower()

    # Allow things like:
    # 3 days
    # 1 day
    # 2 weeks
    # 1 week
    # 1 month
    # 2 months

    parts = duration.split()

    if len(parts) != 2:
        return None

    try:
        amount = int(parts[0])
    except ValueError:
        return None

    unit = parts[1]

    if amount <= 0:
        return None

    if unit in ("day", "days"):
        return datetime.timedelta(days=amount)

    if unit in ("week", "weeks"):
        return datetime.timedelta(weeks=amount)

    if unit in ("month", "months"):
        # 1 month = 30 days
        return datetime.timedelta(days=amount * 30)

    return None


class InactivityUserSelect(discord.ui.UserSelect):

    def __init__(self, view):

        self.parent_view = view

        super().__init__(
            placeholder="Select a user...",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction):

        user = self.values[0]

        existing = get_inactivity(user.id)

        if existing and existing[6] is None:

            return await interaction.response.send_message(
                "❌ This user already has an active inactivity notice.",
                ephemeral=True
            )

        self.parent_view.selected_user = user

        await interaction.response.edit_message(
            content=(
                f"👤 **User:** {user.mention}\n\n"
                "Select the rank:"
            ),
            view=InactivityRankView(
                self.parent_view
            )
        )


class InactivityRankSelect(discord.ui.Select):

    def __init__(self, view):

        self.parent_view = view

        options = [
            discord.SelectOption(
                label="HR",
                value="HR"
            ),
            discord.SelectOption(
                label="SHR",
                value="SHR"
            )
        ]

        super().__init__(
            placeholder="Select rank...",
            options=options
        )

    async def callback(self, interaction):

        self.parent_view.selected_rank = self.values[0]

        await interaction.response.edit_message(
            content=(
                f"👤 **User:** "
                f"{self.parent_view.selected_user.mention}\n"
                f"🏷️ **Rank:** "
                f"{self.parent_view.selected_rank}\n\n"
                "Select the duration:"
            ),
            view=InactivityDurationView(
                self.parent_view
            )
        )


class InactivityDurationSelect(discord.ui.Select):

    def __init__(self, view):

        self.parent_view = view

        options = [
            discord.SelectOption(
                label="4 Weeks",
                value="4 weeks",
                description="Normal long-term inactivity."
            ),
            discord.SelectOption(
                label="5 Weeks — Emergency",
                value="5 weeks",
                description="Emergency cases only."
            ),
            discord.SelectOption(
                label="6 Weeks — Emergency",
                value="6 weeks",
                description="Emergency cases only."
            ),
            discord.SelectOption(
                label="Custom Duration",
                value="custom",
                description="Enter your own duration."
            )
        ]

        super().__init__(
            placeholder="Select duration...",
            options=options
        )

    async def callback(self, interaction):

        selected = self.values[0]

        # Custom duration
        if selected == "custom":

            await interaction.response.send_modal(
                InactivityCustomModal(
                    self.parent_view
                )
            )

            return

        # Preset duration
        self.parent_view.duration_text = selected

        if selected in ("5 weeks", "6 weeks"):
            self.parent_view.emergency = True
        else:
            self.parent_view.emergency = False

        await interaction.response.send_modal(
            InactivityReasonModal(
                self.parent_view
            )
        )


class InactivityCustomModal(
    discord.ui.Modal,
    title="Custom Inactivity Duration"
):

    duration = discord.ui.TextInput(
        label="Duration",
        placeholder="Examples: 3 days, 2 weeks, 1 month",
        required=True,
        max_length=50,
        style=discord.TextStyle.short
    )

    reason = discord.ui.TextInput(
        label="Reason (optional)",
        placeholder="Leave empty for 'Not provided'.",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, view):

        super().__init__()

        self.parent_view = view

    async def on_submit(self, interaction):

        duration_text = self.duration.value.strip().lower()

        duration = parse_inactivity_duration(
            duration_text
        )

        if duration is None:

            return await interaction.response.send_message(
                "❌ Invalid duration.\n\n"
                "Please use a format such as:\n"
                "• `3 days`\n"
                "• `1 week`\n"
                "• `2 weeks`\n"
                "• `1 month`\n"
                "• `2 months`",
                ephemeral=True
            )

        self.parent_view.duration_text = duration_text

        # 5+ weeks automatically count as emergency
        total_days = duration.total_seconds() / 86400

        self.parent_view.emergency = (
            total_days >= 35
        )

        await create_inactivity(
            interaction,
            self.parent_view,
            duration,
            self.reason.value.strip()
        )


class InactivityReasonModal(
    discord.ui.Modal,
    title="Inactivity Notice"
):

    reason = discord.ui.TextInput(
        label="Reason (optional)",
        placeholder="Leave empty for 'Not provided'.",
        required=False,
        max_length=500,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, view):

        super().__init__()

        self.parent_view = view

    async def on_submit(self, interaction):

        duration = parse_inactivity_duration(
            self.parent_view.duration_text
        )

        if duration is None:

            return await interaction.response.send_message(
                "❌ Invalid duration.",
                ephemeral=True
            )

        await create_inactivity(
            interaction,
            self.parent_view,
            duration,
            self.reason.value.strip()
        )


async def create_inactivity(
    interaction,
    view,
    duration,
    reason
):

    user = view.selected_user
    rank = view.selected_rank
    emergency = view.emergency

    if not reason:
        reason = "Not provided"

    # Check active inactivity
    existing = get_inactivity(user.id)

    if existing and existing[6] is None:

        return await interaction.response.send_message(
            "❌ This user already has an active inactivity notice.",
            ephemeral=True
        )

    # Check cooldown
    last_ended = get_last_ended_inactivity(user.id)

    if last_ended:

        cooldown_end = (
            last_ended
            + INACTIVITY_COOLDOWN_DAYS * 86400
        )

        if int(time.time()) < cooldown_end:

            remaining = (
                cooldown_end
                - int(time.time())
            )

            days = max(
                1,
                remaining // 86400
            )

            return await interaction.response.send_message(
                f"❌ This user is on cooldown. "
                f"They must wait approximately "
                f"**{days} more day(s)**.",
                ephemeral=True
            )

    # Current German time
    now = datetime.datetime.now(
        GERMANY_TZ
    )

    # Calculate the end date.
    # The inactivity always ends at 06:00.
    end_date = (
        now + duration
    ).date()

    end_datetime = datetime.datetime.combine(
        end_date,
        datetime.time(
            6,
            0,
            0
        ),
        tzinfo=GERMANY_TZ
    )

    start_timestamp = int(
        now.timestamp()
    )

    end_timestamp = int(
        end_datetime.timestamp()
    )

    # Save
    add_inactivity(
        user.id,
        rank,
        reason,
        start_timestamp,
        end_timestamp,
        emergency
    )

    # Give inactivity role
    role = interaction.guild.get_role(
        INACTIVITY_ROLE
    )

    if role:

        try:

            await user.add_roles(
                role,
                reason=(
                    f"Inactivity issued by "
                    f"{interaction.user}"
                )
            )

        except discord.Forbidden:

            finish_inactivity(
                user.id
            )

            return await interaction.response.send_message(
                "❌ I couldn't give the inactivity role. "
                "Please make sure Adelina's role is above "
                "the inactivity role.",
                ephemeral=True
            )

    date_text = end_datetime.strftime(
        "%d/%m/%Y"
    )

    # DM
    embed = discord.Embed(
        title="Inactivity Logged!",
        description=(
            f"Greetings, {user.mention}! "
            f"Your inactivity notice has been approved "
            f"and will end at **{date_text}**."
        ),
        color=0x5865F2
    )

    embed.add_field(
        name="Reason",
        value=reason,
        inline=False
    )

    embed.add_field(
        name="Information",
        value=(
            "You are responsible for knowing when it ends. "
            "For any questions feel free to ask an HR+. "
            "Enjoy your break!"
        ),
        inline=False
    )

    try:

        await user.send(
            embed=embed
        )

    except discord.Forbidden:
        pass

    # Confirmation
    await interaction.response.send_message(
        f"✅ Inactivity logged for "
        f"{user.mention} until **{date_text}**.",
        ephemeral=True
    )


class InactivityStartView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=120
        )

        self.selected_user = None
        self.selected_rank = None
        self.duration_text = None
        self.emergency = False

        self.add_item(
            InactivityUserSelect(self)
        )


class InactivityRankView(discord.ui.View):

    def __init__(self, previous_view):

        super().__init__(
            timeout=120
        )

        self.selected_user = (
            previous_view.selected_user
        )

        self.selected_rank = None
        self.duration_text = None
        self.emergency = False

        self.add_item(
            InactivityRankSelect(self)
        )


class InactivityDurationView(discord.ui.View):

    def __init__(self, previous_view):

        super().__init__(
            timeout=120
        )

        self.selected_user = (
            previous_view.selected_user
        )

        self.selected_rank = (
            previous_view.selected_rank
        )

        self.duration_text = None
        self.emergency = False

        self.add_item(
            InactivityDurationSelect(self)
        )


# ============================================================
# /INACTIVITY
# ============================================================

@tree.command(
    name="inactivity",
    description="Place a user on inactivity."
)
async def inactivity(interaction):

    if await deny_dm(interaction):
        return

    if not can_inactivity(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    await interaction.response.send_message(
        "Select the user who will be placed on inactivity:",
        view=InactivityStartView(),
        ephemeral=True
    )

# ============================================================
# /UNINACTIVITY
# ============================================================

class UninactivitySelect(discord.ui.UserSelect):

    def __init__(self):

        super().__init__(
            placeholder="Select a user...",
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction):

        user = self.values[0]

        record = get_inactivity(
            user.id
        )

        if not record or record[6] is not None:

            return await interaction.response.send_message(
                "❌ This user does not have an active inactivity notice.",
                ephemeral=True
            )

        role = interaction.guild.get_role(
            INACTIVITY_ROLE
        )

        if role and role in user.roles:

            try:

                await user.remove_roles(
                    role,
                    reason=(
                        f"Inactivity ended by "
                        f"{interaction.user}"
                    )
                )

            except discord.Forbidden:

                return await interaction.response.send_message(
                    "❌ I couldn't remove the inactivity role.",
                    ephemeral=True
                )

        finish_inactivity(
            user.id
        )

        channel = interaction.guild.get_channel(
            INACTIVITY_LOG_CHANNEL
        )

        if channel:

            embed = discord.Embed(
                description=(
                    f"Greetings, {user.mention}! "
                    "Your inactivity notice has ended today, "
                    "welcome back!\n\n"
                    "For any questions or concerns feel free "
                    "to ask an HR+."
                ),
                color=0x57F287
            )

            await channel.send(
                embed=embed
            )

        await interaction.response.send_message(
            f"✅ Inactivity for {user.mention} "
            "has been ended.",
            ephemeral=True
        )


class UninactivityView(discord.ui.View):

    def __init__(self):

        super().__init__(
            timeout=120
        )

        self.add_item(
            UninactivitySelect()
        )


@tree.command(
    name="uninactivity",
    description="End a user's inactivity early."
)
async def uninactivity(interaction):

    if await deny_dm(interaction):
        return

    if not can_inactivity(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    await interaction.response.send_message(
        "Select the user whose inactivity should end:",
        view=UninactivityView(),
        ephemeral=True
    )


# ============================================================
# /INACTIVITYLOGS
# ============================================================

@tree.command(
    name="inactivitylogs",
    description="Show users currently on inactivity."
)
async def inactivitylogs(interaction):

    if await deny_dm(interaction):
        return

    if not can_inactivity(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    rows = get_active_inactivities()

    if not rows:

        return await interaction.response.send_message(
            "There are **no active inactivity notices**.",
            ephemeral=True
        )

    embed = discord.Embed(
        title=f"📋 Active Inactivity Notices — {SERVER_NAME}",
        color=0x5865F2
    )

    for (
        user_id,
        rank,
        reason,
        start_timestamp,
        end_timestamp,
        emergency
    ) in rows:

        member = interaction.guild.get_member(
            int(user_id)
        )

        if member:
            user_name = member.mention
        else:
            user_name = f"User ID {user_id}"

        end_date = datetime.datetime.fromtimestamp(
            end_timestamp,
            GERMANY_TZ
        ).strftime("%d/%m/%Y")

        emergency_text = (
            " 🚨 Emergency"
            if emergency
            else ""
        )

        embed.add_field(
            name=(
                f"{user_name} — "
                f"{rank}"
                f"{emergency_text}"
            ),
            value=(
                f"**Ends:** {end_date}\n"
                f"**Reason:** {reason}"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# ON READY
# ============================================================

@bot.event
async def on_ready():
    guild = bot.get_guild(GUILD_ID)

    if guild:
        # ZUERST die vorhandenen Commands auf den Server kopieren
        bot.tree.copy_global_to(guild=guild)
        synced = await bot.tree.sync(guild=guild)

        print(f"Synced {len(synced)} commands to {guild.name}.")

        # Danach die globalen Commands entfernen,
        # damit sie nicht doppelt erscheinen
        bot.tree.clear_commands(guild=None)
        await bot.tree.sync()

    if not cleanup_old_warnings.is_running():
        cleanup_old_warnings.start()

    if not cleanup_old_history.is_running():
        cleanup_old_history.start()

    if not process_inactivities.is_running():
        process_inactivities.start()

    await bot.change_presence(
        activity=discord.Game("⚖️ Monitoring the community server.")
    )

    print(
        f"{BOT_NAME} is online as {bot.user} in "
        f"{guild.name if guild else 'Unknown Guild'}."
    )
    
# ============================================================
# /WARN
# ============================================================

@tree.command(
    name="warn",
    description="Warn a user."
)
async def warn(
    interaction,
    member: discord.Member,
    reason: str
):

    if await deny_dm(interaction):
        return

    if not can_warn(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    if interaction.user.id == member.id:

        return await interaction.response.send_message(
            "❌ You cannot warn yourself.",
            ephemeral=True
        )

    if member.id == bot.user.id:

        return await interaction.response.send_message(
            "❌ You cannot warn Adelina.",
            ephemeral=True
        )

    if has_role(member, SECRETARY_ROLE):

        return await interaction.response.send_message(
            "❌ You cannot warn a Secretary.",
            ephemeral=True
        )

    if has_role(member, MOTHER_ADELINÈ_ROLE):

        return await interaction.response.send_message(
            "❌ You cannot warn a Mother Adelinè.",
            ephemeral=True
        )

    if has_role(member, SHR_ROLE):

        return await interaction.response.send_message(
            "❌ You cannot warn an SHR.",
            ephemeral=True
        )

    add_warning(
        member.id,
        reason
    )

    count = count_warnings(
        member.id
    )

    log_action(
        member.id,
        interaction.user.id,
        "warn",
        reason
    )

    rank = get_staff_rank(
        interaction.user
    )

    embed = discord.Embed(
        title=f"⚠️ You have been warned at {SERVER_NAME}.",
        color=0xFFCC00
    )

    embed.add_field(
        name="Reason",
        value=reason,
        inline=False
    )

    embed.add_field(
        name="Warnings",
        value=f"{count}/3",
        inline=False
    )

    embed.add_field(
        name="Appeal",
        value=APPEAL_LINK,
        inline=False
    )

    embed.add_field(
        name="Warning issued by",
        value=rank,
        inline=False
    )

    try:
        await member.send(
            embed=embed
        )
    except:
        pass

    log_channel = interaction.guild.get_channel(
        WARN_LOG_CHANNEL
    )

    if log_channel:

        log_embed = discord.Embed(
            title="⚠️ Someone received a warning.",
            color=0xFFCC00
        )

        log_embed.add_field(
            name="Warning issued by",
            value=interaction.user.mention,
            inline=False
        )

        log_embed.add_field(
            name="Person who received the warning",
            value=member.mention,
            inline=False
        )

        log_embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )

        log_embed.add_field(
            name="Time",
            value=datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            inline=False
        )

        await log_channel.send(
            embed=log_embed
        )

    await interaction.response.send_message(
        f"{member.mention} has been warned ({count}/3).",
        ephemeral=True
    )


# ============================================================
# /UNWARN
# ============================================================

@tree.command(
    name="unwarn",
    description="Remove one warning."
)
async def unwarn(
    interaction,
    member: discord.Member
):

    if await deny_dm(interaction):
        return

    if not can_warn(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

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

    remove_one_warning(
        member.id
    )

    count = count_warnings(
        member.id
    )

    log_action(
        member.id,
        interaction.user.id,
        "unwarn",
        "Removed one warning"
    )

    embed = discord.Embed(
        title=(
            f"✅ One of your warnings has been "
            f"removed at {SERVER_NAME}."
        ),
        color=0x57F287
    )

    embed.add_field(
        name="You now have",
        value=f"{count}/3 warnings.",
        inline=False
    )

    try:
        await member.send(
            embed=embed
        )
    except:
        pass

    await interaction.response.send_message(
        f"Removed one warning from "
        f"{member.mention}. ({count}/3)",
        ephemeral=True
    )


# ============================================================
# /WARNINGS
# ============================================================

@tree.command(
    name="warnings",
    description="Show all users with active warnings."
)
async def warnings_cmd(interaction):

    if await deny_dm(interaction):
        return

    if not has_role(
        interaction.user,
        SHR_ROLE
    ):

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

        warnings_list = get_all_warnings(
            user_id
        )

        member = interaction.guild.get_member(
            int(user_id)
        )

        name = (
            member.display_name
            if member
            else f"User ID {user_id}"
        )

        value_text = ""

        for index, (
            reason,
            timestamp
        ) in enumerate(
            warnings_list,
            start=1
        ):

            warn_date = datetime.datetime.fromtimestamp(
                timestamp
            ).strftime("%Y-%m-%d")

            expires_at = (
                timestamp
                + 30 * 24 * 60 * 60
            )

            remaining = (
                expires_at
                - int(time.time())
            )

            if remaining > 0:

                expires_text = (
                    f"{remaining // 86400} days left"
                )

            else:

                expires_text = (
                    "Expired (auto-remove soon)"
                )

            value_text += (
                f"**Warning {index}:** {reason}\n"
                f"• Date: {warn_date}\n"
                f"• Expires: {expires_text}\n\n"
            )

        embed.add_field(
            name=name,
            value=value_text,
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# /BAN
# ============================================================

@tree.command(
    name="ban",
    description="Ban a user."
)
async def ban(
    interaction,
    member: discord.Member,
    reason: str
):

    if await deny_dm(interaction):
        return

    if not can_ban(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    try:

        await member.send(
            f"⛔ You have been banned from "
            f"{SERVER_NAME}.\n"
            f"Reason: {reason}\n"
            f"Appeal: {APPEAL_LINK}"
        )

    except:
        pass

    await member.ban(
        reason=reason
    )

    log_action(
        member.id,
        interaction.user.id,
        "ban",
        reason
    )

    log_channel = interaction.guild.get_channel(
        BAN_LOG_CHANNEL
    )

    if log_channel:

        log_embed = discord.Embed(
            title="⛔ Someone got banned.",
            color=0xFF0000
        )

        log_embed.add_field(
            name="Banned by",
            value=interaction.user.mention,
            inline=False
        )

        log_embed.add_field(
            name="Person banned",
            value=member.mention,
            inline=False
        )

        log_embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )

        log_embed.add_field(
            name="Time",
            value=datetime.datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
            inline=False
        )

        await log_channel.send(
            embed=log_embed
        )

    await interaction.response.send_message(
        f"{member.mention} has been banned.",
        ephemeral=True
    )


# ============================================================
# /HISTORY
# ============================================================

@tree.command(
    name="history",
    description="Show full moderation history of all users."
)
async def history(interaction):

    if await deny_dm(interaction):
        return

    if not has_role(
        interaction.user,
        SHR_ROLE
    ):

        return await interaction.response.send_message(
            "❌ Only SHR can view the full moderation history.",
            ephemeral=True
        )

    conn = db_connect()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            user_id,
            staff_id,
            action,
            reason,
            timestamp
        FROM moderation_log
        ORDER BY timestamp DESC
        """
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
        color=0x2B2D31
    )

    for (
        user_id,
        staff_id,
        action,
        reason,
        timestamp
    ) in rows:

        member = interaction.guild.get_member(
            int(user_id)
        )

        user_name = (
            member.display_name
            if member
            else f"User ID {user_id}"
        )

        staff_member = interaction.guild.get_member(
            int(staff_id)
        )

        staff_name = (
            staff_member.display_name
            if staff_member
            else f"Staff ID {staff_id}"
        )

        date = datetime.datetime.fromtimestamp(
            timestamp
        ).strftime("%Y-%m-%d %H:%M")

        embed.add_field(
            name=f"{action.upper()} — {date}",
            value=(
                f"**User:** {user_name}\n"
                f"**Reason:** {reason}\n"
                f"**Staff:** {staff_name}"
            ),
            inline=False
        )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# ANNOUNCEMENT UI
# ============================================================

class UserSelect(discord.ui.UserSelect):

    def __init__(
        self,
        message,
        channel,
        embed_mode
    ):

        super().__init__(
            placeholder="Select a user to ping...",
            min_values=1,
            max_values=1
        )

        self.message = message
        self.channel = channel
        self.embed_mode = embed_mode

    async def callback(self, interaction):

        selected_user = self.values[0]

        if self.embed_mode:

            embed = discord.Embed(
                title=f"📢 Announcement — {SERVER_NAME}",
                description=self.message,
                color=0x5865F2
            )

            await self.channel.send(
                content=selected_user.mention,
                embed=embed
            )

        else:

            await self.channel.send(
                f"{selected_user.mention} "
                f"{self.message}"
            )

        await interaction.response.send_message(
            "Announcement sent.",
            ephemeral=True
        )


class PingSelect(discord.ui.Select):

    def __init__(
        self,
        message,
        channel,
        embed_mode
    ):

        self.message = message
        self.channel = channel
        self.embed_mode = embed_mode

        options = [
            discord.SelectOption(
                label="None",
                value="none"
            ),
            discord.SelectOption(
                label="@everyone",
                value="everyone"
            ),
            discord.SelectOption(
                label="@here",
                value="here"
            ),
            discord.SelectOption(
                label="Ping a User",
                value="user"
            )
        ]

        super().__init__(
            placeholder="Choose ping type...",
            options=options
        )

    async def callback(self, interaction):

        ping = self.values[0]

        if ping == "none":

            if self.embed_mode:

                embed = discord.Embed(
                    title=f"📢 Announcement — {SERVER_NAME}",
                    description=self.message,
                    color=0x5865F2
                )

                await self.channel.send(
                    embed=embed
                )

            else:

                await self.channel.send(
                    self.message
                )

            return await interaction.response.send_message(
                "Announcement sent.",
                ephemeral=True
            )

        if ping == "everyone":

            if self.embed_mode:

                embed = discord.Embed(
                    title=f"📢 Announcement — {SERVER_NAME}",
                    description=self.message,
                    color=0x5865F2
                )

                await self.channel.send(
                    content="@everyone",
                    embed=embed
                )

            else:

                await self.channel.send(
                    f"@everyone {self.message}"
                )

            return await interaction.response.send_message(
                "Announcement sent.",
                ephemeral=True
            )

        if ping == "here":

            if self.embed_mode:

                embed = discord.Embed(
                    title=f"📢 Announcement — {SERVER_NAME}",
                    description=self.message,
                    color=0x5865F2
                )

                await self.channel.send(
                    content="@here",
                    embed=embed
                )

            else:

                await self.channel.send(
                    f"@here {self.message}"
                )

            return await interaction.response.send_message(
                "Announcement sent.",
                ephemeral=True
            )

        if ping == "user":

            view = discord.ui.View(
                timeout=60
            )

            view.add_item(
                UserSelect(
                    self.message,
                    self.channel,
                    self.embed_mode
                )
            )

            return await interaction.response.send_message(
                "Select a user to ping:",
                view=view,
                ephemeral=True
            )


class PingView(discord.ui.View):

    def __init__(
        self,
        message,
        channel,
        embed_mode
    ):

        super().__init__(
            timeout=60
        )

        self.add_item(
            PingSelect(
                message,
                channel,
                embed_mode
            )
        )


# ============================================================
# /ANNOUNCE
# ============================================================

@tree.command(
    name="announce",
    description="Send an announcement with an embed."
)
async def announce(
    interaction,
    message: str,
    channel: discord.TextChannel
):

    if await deny_dm(interaction):
        return

    if not can_announce(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    view = PingView(
        message,
        channel,
        True
    )

    await interaction.response.send_message(
        "Select ping type:",
        view=view,
        ephemeral=True
    )


# ============================================================
# /ANNOUNCE_TEXT
# ============================================================

@tree.command(
    name="announce_text",
    description="Send an announcement without an embed."
)
async def announce_text(
    interaction,
    message: str,
    channel: discord.TextChannel
):

    if await deny_dm(interaction):
        return

    if not can_announce(interaction.user):

        return await interaction.response.send_message(
            "❌ No permission.",
            ephemeral=True
        )

    view = PingView(
        message,
        channel,
        False
    )

    await interaction.response.send_message(
        "Select ping type:",
        view=view,
        ephemeral=True
    )


# ============================================================
# /DASHBOARD
# ============================================================

@tree.command(
    name="dashboard",
    description="Shows moderation tools."
)
async def dashboard(interaction):

    if await deny_dm(interaction):
        return

    embed = discord.Embed(
        title=f"🛠️ Moderation Dashboard — {SERVER_NAME}",
        description=(
            "**HR:** /warn, /unwarn, /inactivity, "
            "/uninactivity, /inactivitylogs\n"
            "**SHR:** /warn, /unwarn, /ban, /warnings, "
            "/history, /inactivity, /uninactivity, "
            "/inactivitylogs\n"
            "**Secretary / Mother Adelinè:** /warn, /unwarn, "
            "/ban, /announce, /announce_text, /inactivity, "
            "/uninactivity, /inactivitylogs\n"
            "**Everyone:** /logs"
        ),
        color=0x2B2D31
    )

    await interaction.response.send_message(
        embed=embed,
        ephemeral=True
    )


# ============================================================
# BOT START
# ============================================================

TOKEN = os.getenv("TOKEN")

if not TOKEN:

    print(
        "❌ ERROR: No TOKEN found in environment variables."
    )

else:

    bot.run(TOKEN)
