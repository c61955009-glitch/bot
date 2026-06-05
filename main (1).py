import discord
from discord.ext import commands
import asyncio
import sqlite3
import random
from datetime import datetime, timedelta, timezone

# ================= НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ БОТА =================
TOKEN = "MTQ2MzEyMDA4NTAwOTgyNjAyOA.GEL6_Y.KH6OLuV4FulfgORSVZHLXhbOAs8Ye-fKZIFQ0Y"

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

APPLICATION_CHANNEL_ID = 1456978286826749982
REVIEW_ROLE_ID = 1461828508035846287
BANK_ROLE_ID = 1434290817450639493
YOUR_USER_ID = 1387442693738729695
NITRO_CATEGORY_ID = 1204154157196648478
NITRO_REVIEW_ROLE_ID = 1442608414676090992
REWARD_ROLE_ID = 1435263220959940648

# ССЫЛКИ НА ГИФКИ
GIF_ORDER = "https://auto.creavite.co/api/out/J48xNyvL88gjtems8b_standard.gif"
GIF_WIN = "https://auto.creavite.co/api/out/HMTa14DEo4gEtems6h_standard.gif"
GIF_HELP = "https://auto.creavite.co/api/out/MFUf5j5tGRH9temsa8_standard.gif"


# ================= ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ДЛЯ РУЛЕТКИ =================
def init_db():
    conn = sqlite3.connect("roulette_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roulette_cooldowns (
            user_id INTEGER PRIMARY KEY,
            last_spin TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()


# ================= ФУНКЦИИ КУЛДАУНА РУЛЕТКИ =================
def check_roulette_cooldown(user_id: int):
    conn = sqlite3.connect("roulette_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT last_spin FROM roulette_cooldowns WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        last_spin_time = datetime.fromisoformat(row[0])
        if last_spin_time.tzinfo is None:
            last_spin_time = last_spin_time.replace(tzinfo=timezone.utc)
        
        if datetime.now(timezone.utc) < last_spin_time + timedelta(hours=24):
            return last_spin_time + timedelta(hours=24)
    return None

def update_roulette_cooldown(user_id: int):
    conn = sqlite3.connect("roulette_data.db")
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    cursor.execute("INSERT OR REPLACE INTO roulette_cooldowns (user_id, last_spin) VALUES (?, ?)", (user_id, now_str))
    conn.commit()
    conn.close()


# ================= ЛОГИКА РУЛЕТКИ С ТВОИМ ДИЗАЙНОМ =================
def spin_roulette_logic(user: discord.Member or discord.User):
    cooldown_end = check_roulette_cooldown(user.id)

    if cooldown_end:
        remaining = cooldown_end - datetime.now(timezone.utc)
        hours, remainder = divmod(int(remaining.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        embed_err = discord.Embed(
            title="⏳ Доступ ограничен",
            description=f"Вы уже крутили рулетку!\nПовторная прокрутка будет доступна через: **{hours} ч. {minutes} мин.**", 
            color=0xe74c3c
        )
        return False, embed_err

    prizes = [
        {"name": "Ничего (Повезет в следующий раз!)", "weight": 70.0},
        {"name": "700 orbs", "weight": 20.0},
        {"name": "1400 orbs", "weight": 8.0},
        {"name": "VIP", "weight": 1.9},
        {"name": "Скидка 100%", "weight": 0.1}
    ]
    
    chosen_prize = random.choices(prizes, weights=[p["weight"] for p in prizes], k=1)[0]
    update_roulette_cooldown(user.id)

    embed = discord.Embed(
        title="🎰 Результат прокрутки!",
        description=(
            f"{user.mention} испытал удачу в ежедневной рулетке!\n\n"
            f"🎁 Ваш выигрыш: **{chosen_prize['name']}**\n\n"
            f"*Если вы выбили ценный приз, сделайте скриншот и обратитесь к администрации сервера.*"
        ),
        color=0x2ecc71 if chosen_prize['name'] != "Ничего (Повезет в следующий раз!)" else 0x95a5a6
    )
    if chosen_prize['name'] in ["VIP", "Скидка 100%"]:
        embed.set_image(url=GIF_WIN)
        
    return True, embed


# ================= МОДАЛЬНЫЕ ОКНА =================

class AccountDataModal(discord.ui.Modal, title="Передача данных от аккаунта"):
    login = discord.ui.TextInput(label="Логин / Почта", placeholder="example@gmail.com или никнейм", required=True)
    password = discord.ui.TextInput(label="Пароль", placeholder="Ваш пароль", style=discord.TextStyle.short, required=True)

    def __init__(self, view: discord.ui.View):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: discord.Interaction):
        self.view.account_login = self.login.value
        self.view.account_password = self.password.value
        
        for child in self.view.children:
            if child.custom_id == "submit_credentials_btn":
                child.disabled = True
                child.label = "Данные переданы"
                child.style = discord.ButtonStyle.secondary

        await interaction.response.edit_message(view=self.view)
        
        await interaction.channel.send(
            f"🔒 <@&{NITRO_REVIEW_ROLE_ID}> **Клиент успешно передал данные от аккаунта!**\n"
            f"Продавец может посмотреть их скрытым сообщением с помощью кнопки настроек выше."
        )


class AddItemModal(discord.ui.Modal, title="Добавить товар в заказ"):
    item_name = discord.ui.TextInput(label="Название товара", placeholder="Например: Nitro Classic 1 месяц", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"➕ **Клиент хочет добавить товар в заказ:** {self.item_name.value}",
            ephemeral=False
        )


class PromoModal(discord.ui.Modal, title="Использовать промокод"):
    promo_code = discord.ui.TextInput(label="Введите промокод", placeholder="Например: FREEORBS2025", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🎫 **Клиент применил промокод:** `{self.promo_code.value}`\nОжидайте проверки промокода продавцом.",
            ephemeral=False
        )


# ================= ВЫПАДАЮЩИЕ МЕНЮ =================

class TransferStaffSelect(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(placeholder="Выберите продавца для передачи тикета...", min_values=1, max_values=1, custom_id="transfer_staff_select")

    async def callback(self, interaction: discord.Interaction):
        target_user = self.values[0]
        member_roles = [role.id for role in interaction.user.roles]
        if NITRO_REVIEW_ROLE_ID not in member_roles and interaction.user.id != YOUR_USER_ID:
            await interaction.response.send_message("❌ Вы не можете передавать тикеты!", ephemeral=True)
            return

        await interaction.channel.set_permissions(target_user, view_channel=True, send_messages=True, read_message_history=True)
        
        await interaction.response.send_message(
            f"🔄 <@&{NITRO_REVIEW_ROLE_ID}> **Тикет передан!**\n"
            f"Продавец {target_user.mention} назначен ответственным за этот заказ.",
            ephemeral=False
        )


# ================= КНОПКИ ВНУТРИ ТИКЕТОВ =================

class TicketSettingsView(discord.ui.View):
    """Скрытая панель настроек для селлеров, чтобы не захламлять основной чат тикета."""
    def __init__(self, parent_view: "TicketOrderView"):
        super().__init__(timeout=180)
        self.parent_view = parent_view

    def is_seller(self, user: discord.Member) -> bool:
        return self.parent_view.is_seller(user)

    @discord.ui.button(label="Продавец занят", style=discord.ButtonStyle.danger, emoji="🚫", custom_id="seller_busy_btn")
    async def seller_busy(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user): return
        owner = interaction.guild.get_member(self.parent_view.ticket_owner_id)
        await interaction.response.send_message(f"🚫 **Стафф сейчас занят.** {owner.mention}, пожалуйста, ожидайте!", ephemeral=False)
        try: await owner.send("Магазин сейчас занят, мы скоро ответим!")
        except: pass

    @discord.ui.button(label="Просмотр данных", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji.from_str("<:1470556709914284083:1508839853041651782>"), custom_id="settings_view_creds")
    async def view_credentials(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ У вас нет доступа к просмотру этих данных!", ephemeral=True)
            return

        if not self.parent_view.account_login or not self.parent_view.account_password:
            await interaction.response.send_message("⚠️ Клиент еще не заполнил форму с данными.", ephemeral=True)
            return

        embed = discord.Embed(title="🔑 Данные авторизации", color=0x9b59b6)
        embed.add_field(name="Логин / Почта", value=f"`{self.parent_view.account_login}`", inline=False)
        embed.add_field(name="Пароль", value=f"`{self.parent_view.account_password}`", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Запросить код-2FA", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<:1496137230765527245:1508839678738960465>"), custom_id="settings_req_2fa")
    async def request_2fa(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Только стафф может запрашивать код!", ephemeral=True)
            return

        owner = interaction.guild.get_member(self.parent_view.ticket_owner_id)
        if not owner:
            await interaction.response.send_message("❌ Клиент не найден на сервере.", ephemeral=True)
            return

        await interaction.response.defer()
        await interaction.channel.send(f"⚠️ {owner.mention}, **продавцу необходим код двухфакторной аутентификации (2FA)!** Пожалуйста, отправьте его сюда в чат.")

        try:
            dm_embed = discord.Embed(
                title="🛒 Магазин TJMS | Требуется код!",
                description="Продавец пытается войти на ваш аккаунт. Пожалуйста, зайдите в тикет и напишите код подтверждения!",
                color=0xe74c3c
            )
            await owner.send(embed=dm_embed)
        except discord.Forbidden:
            pass

    @discord.ui.button(label="Подтверждение входа", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<:icons8discord48:1508839678738960465>"), custom_id="settings_req_mail")
    async def request_mail_confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Только стафф может отправлять запрос!", ephemeral=True)
            return

        owner = interaction.guild.get_member(self.parent_view.ticket_owner_id)
        if not owner:
            await interaction.response.send_message("❌ Клиент не найден на сервере.", ephemeral=True)
            return

        await interaction.response.defer()
        
        embed = discord.Embed(
            title="📩 Требуется подтверждение входа по почте!",
            description=(
                f"👋 {owner.mention}, продавец пытается войти на ваш аккаунт, и Discord заблокировал вход до подтверждения по почте.\n\n"
                f"**Пожалуйста, выполните следующие шаги:**\n"
                f"1️⃣ Перейдите в почтовый ящик, привязанный к вашему Discord-аккаунту.\n"
                f"2️⃣ Найдите новое письмо от **Discord** (тема: *«Обнаружен новый адрес входа»*). "
                f"Если письма нет во входящих, обязательно проверьте папку **«Спам»**!\n"
                f"3️⃣ Откройте письмо и нажмите на зелёную кнопку **«Авторизовать вход»** / **«Подтвердить вход»**.\n"
                f"4️⃣ После успешной авторизации **напишите в этот чат**, что вы всё сделали! 💬"
            ),
            color=0xe67e22
        )
        embed.set_footer(text="Магазин TJMS • Безопасность и надёжность")
        
        await interaction.channel.send(content=f"⚠️ {owner.mention}", embed=embed)

        try:
            dm_embed = discord.Embed(
                title="🛒 Магазин TJMS | Подтверждение на почте",
                description="Нам необходимо подтверждение входа по почте. Пожалуйста, зайдите в канал заказа и выполните инструкцию!",
                color=0xe67e22
            )
            await owner.send(embed=dm_embed)
        except discord.Forbidden:
            pass

    @discord.ui.button(label="Ожидание выдачи", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<:1054527061689118800:1508840698873516194>"), custom_id="settings_waiting_order")
    async def waiting_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Только администрация или стафф могут изменить статус заказа!", ephemeral=True)
            return

        owner = interaction.guild.get_member(self.parent_view.ticket_owner_id)
        if not owner:
            await interaction.response.send_message("❌ Не удалось найти создателя тикета на сервере.", ephemeral=True)
            return

        button.disabled = True
        button.label = "В процессе..."
        button.style = discord.ButtonStyle.secondary

        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"⏳ **Стафф перевёл заказ в статус ожидания.** Продавец начал работу над заказом {owner.mention}!")

        try:
            dm_embed = discord.Embed(
                title="🛒 Магазин TJMS | Статус заказа",
                description=(
                    "👋 Привет!\n\n"
                    "**Продавец зашёл на ваш аккаунт.**\n"
                    "Ожидайте ваш заказ, мы сообщим, как только всё будет готово! ✨"
                ),
                color=0x3498db
            )
            await owner.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.channel.send(f"⚠️ Не удалось отправить уведомление в ЛС для {owner.mention}, так как у него закрыта личка.")

    @discord.ui.button(label="Передать тикет", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji.from_str("<:Moderatorpfp:1479391384279449631>"), custom_id="settings_transfer_ticket")
    async def transfer_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Только стафф может передавать тикеты!", ephemeral=True)
            return

        view = discord.ui.View()
        view.add_item(TransferStaffSelect())
        await interaction.response.send_message("Выберите ниже пользователя, которому нужно передать этот тикет:", view=view, ephemeral=True)


class TicketOrderView(discord.ui.View):
    def __init__(self, ticket_owner_id: int):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id
        self.account_login = None
        self.account_password = None
        self.assigned_seller = None

    def is_seller(self, user: discord.Member) -> bool:
        member_roles = [role.id for role in user.roles]
        return NITRO_REVIEW_ROLE_ID in member_roles or user.id == YOUR_USER_ID

    @discord.ui.button(label="Взять заказ на себя", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji.from_str("<:1334529026462843061:1509288976169832468>"), custom_id="claim_order_btn", row=0)
    async def claim_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Только стафф и селлеры могут брать заказы!", ephemeral=True)
            return
        
        self.assigned_seller = interaction.user
        button.disabled = True
        button.label = f"Выполняет: {interaction.user.name}"
        button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"👋 {interaction.user.mention} **взял этот тикет в обработку!** Он скоро ответит вам.")

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str("<:1334524823954784297:1509288911623421992>"), custom_id="close_ticket_btn", row=0)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Только стафф и администрация могут закрывать тикеты!", ephemeral=True)
            return

        await interaction.response.send_message("Удаление канала через 3 секунды...")
        await asyncio.sleep(3)
        await interaction.channel.delete()

    @discord.ui.button(label="Настройки", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji.from_str("<:1334526998852403310:1483784211964887070>"), custom_id="settings_btn", row=0)
    async def settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Доступ к настройкам разрешен только селлеру!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🛠️ Управление тикетом",
            description=(
                f"**Канал заказа:** {interaction.channel.mention}\n"
                f"**Создатель тикета:** <@{self.ticket_owner_id}>\n"
                f"**Ответственный продавец:** {self.assigned_seller.mention if self.assigned_seller else 'Не назначен'}\n\n"
                f"Выберите действие ниже для конфиденциального управления процессом."
            ),
            color=0x7f8c8d
        )
        await interaction.response.send_message(embed=embed, view=TicketSettingsView(self), ephemeral=True)

    @discord.ui.button(label="Добавить товар", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji.from_str("<:1055604055143104543:1508839634098978856>"), custom_id="add_item_btn", row=1)
    async def add_item(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddItemModal())

    @discord.ui.button(label="Использовать промокод", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji.from_str("<:1470556672065011804:1508839917353177168>"), custom_id="use_promo_btn", row=1)
    async def use_promo(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(PromoModal())

    @discord.ui.button(label="Передача данных", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<:1309530439572131881:1483784367275901011>"), custom_id="submit_credentials_btn", row=1)
    async def submit_credentials(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ticket_owner_id:
            await interaction.response.send_message("❌ Только создатель тикета может передать свои данные!", ephemeral=True)
            return
        await interaction.response.send_modal(AccountDataModal(self))

    @discord.ui.button(label="Заказ выполнен", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji.from_str("<:9562blurpleverified:1426554814170529823>"), custom_id="complete_order_btn", row=2)
    async def complete_order(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.is_seller(interaction.user):
            await interaction.response.send_message("❌ Только администрация или стафф могут отметить заказ как выполненный!", ephemeral=True)
            return

        owner = interaction.guild.get_member(self.ticket_owner_id)
        if not owner:
            await interaction.response.send_message("❌ Не удалось найти создателя тикета на сервере.", ephemeral=True)
            return

        reward_role = interaction.guild.get_role(REWARD_ROLE_ID)
        if reward_role:
            try:
                await owner.add_roles(reward_role)
                role_status = f"✅ Роль {reward_role.mention} успешно выдана пользователю {owner.mention}."
            except discord.Forbidden:
                role_status = f"⚠️ Не удалось выдать роль {reward_role.mention} (проверьте права бота)."
        else:
            role_status = "⚠️ Роль для выдачи не найдена."

        for child in self.children:
            if child.custom_id != "close_ticket_btn":
                child.disabled = True
        
        button.label = "Выполнено"
        button.style = discord.ButtonStyle.secondary
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(content=f"🎉 **Стафф отметил, что заказ успешно выполнен!**\n{role_status}", ephemeral=True)
        await interaction.channel.send("🎉 **Стафф отметил, что заказ успешно выполнен!**")

        try:
            dm_embed = discord.Embed(
                title="🛒 Магазин TJMS",
                description="Ваш заказ успешно выполнен! Спасибо, что выбрали нас.",
                color=0x2ecc71
            )
            await owner.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.channel.send(f"⚠️ Напоминание в ЛС для {owner.mention} не отправлено, так как у него закрыты личные сообщения.")


class TicketHelpView(discord.ui.View):
    def __init__(self, ticket_owner_id: int):
        super().__init__(timeout=None)
        self.ticket_owner_id = ticket_owner_id

    @discord.ui.button(label="Закрыть тикет", style=discord.ButtonStyle.danger, emoji=discord.PartialEmoji.from_str("<:1334524823954784297:1509288911623421992>"), custom_id="close_help_ticket_btn", row=0)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        member_roles = [role.id for role in interaction.user.roles]
        if NITRO_REVIEW_ROLE_ID not in member_roles and interaction.user.id != YOUR_USER_ID:
            await interaction.response.send_message("❌ Только стафф и администрация могут закрывать тикеты!", ephemeral=True)
            return

        await interaction.response.send_message("Удаление канала через 3 секунды...")
        await asyncio.sleep(3)
        await interaction.channel.delete()


async def create_private_ticket_channel(interaction: discord.Interaction, prefix: str, category_id: int):
    guild = interaction.guild
    category = guild.get_channel(category_id)
    
    channel_name = f"┗│{prefix}-{interaction.user.name}"
    
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        guild.get_role(NITRO_REVIEW_ROLE_ID): discord.PermissionOverwrite(view_channel=True, send_messages=True)
    }
    return await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)


class OrderModal(discord.ui.Modal, title="Сделать заказ"):
    item = discord.ui.TextInput(label="Товар", placeholder="Например: Nitro Full")
    payment = discord.ui.TextInput(label="Оплата", placeholder="СБП / Крипта / Инвайты")
    
    async def on_submit(self, interaction: discord.Interaction):
        channel = await create_private_ticket_channel(interaction, "🛒заказ", NITRO_CATEGORY_ID)
        
        embed = discord.Embed(title="🛒 Новый заказ", color=0x5865F2, timestamp=interaction.created_at)
        embed.add_field(name="Заказчик", value=interaction.user.mention)
        embed.add_field(name="Товар", value=self.item.value)
        embed.add_field(name="Оплата", value=self.payment.value)
        embed.set_image(url=GIF_ORDER)
        
        await channel.send(content=f"<@&{NITRO_REVIEW_ROLE_ID}>", embed=embed, view=TicketOrderView(interaction.user.id))
        await interaction.response.send_message(f"Тикет создан: {channel.mention}", ephemeral=True)


class MainTicketView(discord.ui.View):
    def __init__(self): 
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Заказать товар", style=discord.ButtonStyle.success, emoji=discord.PartialEmoji.from_str("<:1496137230765527245:1508839678738960465>"), custom_id="btn_order")
    async def order(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OrderModal())
    
    @discord.ui.button(label="Я победил", style=discord.ButtonStyle.primary, emoji=discord.PartialEmoji.from_str("<:1315291449801179156:1483784261042569276>"), custom_id="btn_win")
    async def win(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await create_private_ticket_channel(interaction, "🎁выигрыш", NITRO_CATEGORY_ID)
        
        embed = discord.Embed(title="🎁 Выигрыш", description=f"{interaction.user.mention} утверждает, что выиграл/выполнил заказ! Ожидайте стафф.", color=0x2ecc71)
        embed.set_image(url=GIF_WIN)
        
        await channel.send(content=f"<@&{NITRO_REVIEW_ROLE_ID}>", embed=embed, view=TicketOrderView(interaction.user.id))
        await interaction.response.send_message(f"Тикет создан: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="Помощь", style=discord.ButtonStyle.secondary, emoji=discord.PartialEmoji.from_str("<:1334526998852403310:1483784211964887070>"), custom_id="btn_help")
    async def help_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = await create_private_ticket_channel(interaction, "⚙️помощь", NITRO_CATEGORY_ID)
        
        embed = discord.Embed(title="⚙️ Помощь", description=f"{interaction.user.mention} нужна помощь. Опишите проблему ниже.", color=0x95a5a6)
        embed.set_image(url=GIF_HELP)
        
        await channel.send(embed=embed, view=TicketHelpView(interaction.user.id))
        await interaction.response.send_message(f"Тикет создан: {channel.mention}", ephemeral=True)


class RouletteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Испытать удачу", style=discord.ButtonStyle.success, emoji="🎰", custom_id="btn_spin_roulette_main")
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        success, embed = spin_roulette_logic(interaction.user)
        if success:
            await interaction.response.send_message(content="🎉 **Я победил!**", embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.command()
async def ticket_panel(ctx):
    if ctx.author.id != YOUR_USER_ID: return
    
    embed = discord.Embed(
        description=(
            "<:15679nitrodiamond:1495119956675793006> **Магазин TJMS** — быстро, удобно и надёжно!\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "<:1470556709914284083:1508839853041651782> **Как пользоваться ботом:**\n\n"
            "<:1496137230765527245:1508839678738960465> **Сделать заказ** — нажмите эту кнопку, чтобы оформить новый заказ через тикет. Укажите нужный товар и ожидайте ответа продавца.\n\n"
            "<:1315291449801179156:1483784261042569276> **Я победил** — используйте кнопку после успешного выполнения заказа / выигрыша, чтобы подтвердить результат.\n\n"
            "<:1334526998852403310:1483784211964887070> **Помощь** — если возникли вопросы, проблемы с ботом или нужна консультация, нажмите сюда и администрация поможет вам.\n\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "<:1470556672065011804:1508839917353177168> **Отзывы наших клиентов:**\n"
            "https://discord.com/channels/1088773600040992768/1321801563190071326nn"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "<:15679nitrodiamond:1495119956675793006> **TJMS** — качество, скорость и лучший сервис для каждого клиента <:chpic:1305593943009792112>"
        ), 
        color=0x5865F2
    )
    embed.set_image(url=GIF_ORDER)
    await ctx.send(embed=embed, view=MainTicketView())


@bot.command()
async def roulette_panel(ctx):
    if ctx.author.id != YOUR_USER_ID: return
        
    embed = discord.Embed(
        title="🎰 Ежедневная рулетка TJMS",
        description=(
            "╭━━━━━━━━━━━━━━━━━━━━━━╮\n"
            "<:1315291449801179156:1483784261042569276> Испытай свою удачу!\n"
            "╰━━━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "<:15679nitrodiamond:1495119956675793006> **Возможные призы:**\n"
            "<:43cca33b74104ba089bb4aa3718f4ec0:1493709626338709605> 700 orbs\n"
            "<:43cca33b74104ba089bb4aa3718f4ec0:1493709626338709605> 1400 orbs\n"
            "<:43cca33b74104ba089bb4aa3718f4ec0:1493709626338709605> VIP\n"
            "<:43cca33b74104ba089bb4aa3718f4ec0:1493709626338709605> Скидка 100%\n"
            "<:43cca33b74104ba089bb4aa3718f4ec0:1493709626338709605> Ничего <:2_:1426860863989485651>\n\n"
            "<:1334526998852403310:1483784211964887070> Бесплатная прокрутка доступна\n"
            "1 раз в 24 часа.\n\n"
            "━━━━━━━ • 🎰 • ━━━━━━━\n\n"
            "Нажми кнопку ниже и попробуй\n"
            "выбить самый редкий приз 🍀"
        ),
        color=0xf1c40f
    )
    embed.set_image(url="https://images-ext-1.discordapp.net/external/3m2qz1RGbiNewqindw8jQDcImCgGBLtxaD8GFfpbIP4/https/cdn-icons-png.flaticon.com/512/3522/3522091.png?format=webp&quality=lossless&width=461&height=461")
    await ctx.send(embed=embed, view=RouletteView())


@bot.command(aliases=["рулетка", "spin"])
async def roulette(ctx):
    success, embed = spin_roulette_logic(ctx.author)
    if success:
        await ctx.send(content="🎉 ****", embed=embed)
    else:
        await ctx.send(embed=embed)


@bot.event
async def on_ready():
    bot.add_view(MainTicketView())
    bot.add_view(RouletteView())
    print(f"Бот {bot.user} запущен!")

if __name__ == "__main__":
    bot.run(TOKEN)
