import discord
from discord import app_commands
from discord.ext import commands
import re
import asyncio
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import (
    DISCORD_TOKEN,
    # FT настройки (artytest-main)
    FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME, FT_GOOGLE_FORM_ID,
    FT_WARN_COST, FT_WARNING_COST, FT_VACATION_COST,
    FT_HEADER_ROW_FIRST, FT_HEADER_ROW_SECOND, FT_VACATION_SOURCE_ROW,
    # RW настройки (rwtest-main)
    RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME, RW_GOOGLE_FORM_ID,
    RW_WARN_COST, RW_WARNING_COST, RW_VACATION_COST,
    RW_HEADER_ROW_FIRST, RW_HEADER_ROW_SECOND, RW_VACATION_SOURCE_ROW
)

# ===== ИНИЦИАЛИЗАЦИЯ БОТА =====
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def get_google_service():
    """Получение сервиса Google Drive API"""
    try:
        # Credentials from Render Secret File path or default
        creds_path = os.getenv('GOOGLE_CREDS_PATH', 'credentials.json')
        creds = Credentials.from_service_account_file(creds_path)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"❌ Ошибка Google: {e}")
        return None


def get_sheet(sheet_id, sheet_name):
    """Получение конкретного листа таблицы"""
    try:
        import gspread
        # Credentials from Render Secret File path or default
        creds_path = os.getenv('GOOGLE_CREDS_PATH', 'credentials.json')
        gc = gspread.service_account(filename=creds_path)
        return gc.open_by_key(sheet_id).worksheet(sheet_name)
    except Exception as e:
        print(f"❌ Ошибка Sheets: {e}")
        return None


def normalize_nick(nick: str) -> str:
    """Нормализация ника (удаление скобок)"""
    if not nick:
        return nick
    nick = re.sub(r'\[[^\]]*\]', '', nick)
    nick = re.sub(r'\([^)]*\)', '', nick)
    nick = re.sub(r'\{[^}]*\}', '', nick)
    return nick.strip()


def find_user_by_nick(nick, sheet_id, sheet_name):
    """Поиск пользователя по нику в указанной таблице"""
    sheet = get_sheet(sheet_id, sheet_name)
    if not sheet:
        return None

    try:
        clean_nick = normalize_nick(nick)
        values = sheet.col_values(1)

        for row_num, value in enumerate(values, start=1):
            if normalize_nick(value) == clean_nick:
                row = sheet.row_values(row_num)

                warns_str = row[3] if len(row) > 3 else '0/3'
                warnings_str = row[4] if len(row) > 4 else '0/3'

                try:
                    warns_count = int(warns_str.split('/')[0]) if warns_str else 0
                except:
                    warns_count = 0

                try:
                    warnings_count = int(warnings_str.split('/')[0]) if warnings_str else 0
                except:
                    warnings_count = 0

                return {
                    'row': row_num,
                    'nick': row[0] if len(row) > 0 else '',
                    'position': row[1] if len(row) > 1 else '',
                    'points': row[2] if len(row) > 2 else '0',
                    'warns': warns_str,
                    'warns_count': warns_count,
                    'warnings': warnings_str,
                    'warnings_count': warnings_count,
                    'email': row[5] if len(row) > 5 else '',
                }
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")

    return None


def update_user(sheet_id, sheet_name, row, column, value):
    """Обновление ячейки пользователя"""
    sheet = get_sheet(sheet_id, sheet_name)
    if sheet:
        try:
            sheet.update_cell(row, column, value)
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления: {e}")
    return False


def parse_points(value) -> int:
    """Парсинг баллов из строки"""
    if not value:
        return 0
    s = str(value).strip().replace(' ', '').replace(',', '').replace(' ', '')
    try:
        return int(float(s))
    except:
        return 0


# =========================================================
# КОМАНДЫ FT (artytest-main) - БЕЗ ПРЕФИКСА
# =========================================================

@bot.tree.command(name="help", description="Показать список всех команд")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Список команд Staff Bot",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🔑 Доступ (FT)",
        value=(
            "`/выдатьдоступ email ник` — выдать доступ к таблице и форме FT\n"
            "`/забратьдоступ email` — забрать доступ к таблице и форме FT"
        ),
        inline=False
    )
    embed.add_field(
        name="💰 Баллы (FT)",
        value=(
            "`/выдатьбаллы ник кол-во` — выдать баллы сотруднику FT\n"
            "`/снятьбаллы ник кол-во` — снять баллы у сотрудника FT\n"
            f"`/снятьварн ник` — снять 1 варн за {FT_WARN_COST} баллов\n"
            f"`/снятьустник ник` — снять 1 устник за {FT_WARNING_COST} баллов"
        ),
        inline=False
    )
    embed.add_field(
        name="⚠️ Наказания (FT)",
        value=(
            "`/выдатьустник ник кол-во` — выдать устник FT (3 устника = 1 варн)\n"
            "`/выдатьварн ник кол-во` — выдать варн FT"
        ),
        inline=False
    )
    embed.add_field(
        name="🔑 Доступ (RW)",
        value=(
            "`/выдатьдоступrw email ник` — выдать доступ к таблице и форме RW\n"
            "`/забратьдоступrw email` — забрать доступ к таблице и форме RW"
        ),
        inline=False
    )
    embed.add_field(
        name="💰 Баллы (RW)",
        value=(
            "`/выдатьбаллыrw ник кол-во` — выдать баллы сотруднику RW\n"
            "`/снятьбаллыrw ник кол-во` — снять баллы у сотрудника RW\n"
            f"`/снятьварнrw ник` — снять 1 варн за {RW_WARN_COST} баллов\n"
            f"`/снятьустникrw ник` — снять 1 устник за {RW_WARNING_COST} баллов"
        ),
        inline=False
    )
    embed.add_field(
        name="⚠️ Наказания (RW)",
        value=(
            "`/выдатьустникrw ник кол-во` — выдать устник RW (3 устника = 1 варн)\n"
            "`/выдатьварнrw ник кол-во` — выдать варн RW"
        ),
        inline=False
    )
    embed.add_field(
        name="📊 Статистика",
        value=(
            "`/stat ник` — показать статистику сотрудника FT\n"
            "`/statrw ник` — показать статистику сотрудника RW"
        ),
        inline=False
    )
    embed.set_footer(text="Тг разработчика • @svets1337")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="выдатьдоступ", description="[FT] Выдать доступ к таблице и форме по email")
@app_commands.describe(email="Email пользователя", nick="Ник сотрудника (кому выдаётся доступ)")
async def grant_access(interaction: discord.Interaction, email: str, nick: str):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        email = email.strip().lower()
        nick = nick.strip()

        if not email or '@' not in email:
            await interaction.followup.send("❌ Укажите корректный email.")
            return

        if not nick:
            await interaction.followup.send("❌ Укажите ник сотрудника.")
            return

        service = get_google_service()
        if not service:
            await interaction.followup.send("❌ Ошибка подключения к Google API.")
            return

        results = []

        try:
            service.permissions().create(
                fileId=FT_GOOGLE_SHEETS_ID,
                body={"type": "user", "role": "reader", "emailAddress": email},
                sendNotificationEmail=True
            ).execute()
            results.append("✅ Доступ к таблице выдан.")
        except Exception as e:
            if "already exists" in str(e).lower():
                results.append("⚠️ Доступ к таблице уже был выдан.")
            else:
                results.append(f"❌ Ошибка таблицы: {str(e)[:100]}")

        form_id = FT_GOOGLE_FORM_ID
        if "/d/" in form_id:
            form_id = form_id.split("/d/")[1].split("/")[0]
        elif "/e/" in form_id:
            form_id = form_id.split("/e/")[1].split("/")[0]

        if form_id:
            try:
                service.permissions().create(
                    fileId=form_id,
                    body={"type": "user", "role": "reader", "emailAddress": email, "view": "published"},
                    sendNotificationEmail=True
                ).execute()
                results.append("✅ Доступ к форме выдан.")
            except Exception as e:
                if "already exists" in str(e).lower():
                    results.append("⚠️ Доступ к форме уже был выдан.")
                else:
                    results.append(f"❌ Ошибка формы: {str(e)[:100]}")
        else:
            results.append("❌ ID формы не указан.")

        embed = discord.Embed(
            title="🔑 Выдача доступа • FTstaff",
            color=discord.Color.green() if not any(r.startswith("❌") for r in results) else discord.Color.red(),
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="📧 Email", value=email, inline=True)
        embed.add_field(name="📋 Результат", value="\n".join(results), inline=False)
        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="забратьдоступ", description="[FT] Забрать доступ к таблице и форме по email")
@app_commands.describe(email="Email пользователя")
async def revoke_access(interaction: discord.Interaction, email: str):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        email = email.strip().lower()

        if not email or '@' not in email:
            await interaction.followup.send("❌ Укажите корректный email.")
            return

        service = get_google_service()
        if not service:
            await interaction.followup.send("❌ Ошибка подключения к Google API.")
            return

        results = []

        def remove_permission(file_id, email, file_name):
            try:
                permissions = service.permissions().list(
                    fileId=file_id,
                    fields="permissions(id, emailAddress, type)"
                ).execute()

                for perm in permissions.get('permissions', []):
                    if perm.get('type') == 'user' and perm.get('emailAddress', '').lower() == email:
                        service.permissions().delete(fileId=file_id, permissionId=perm['id']).execute()
                        return f"✅ Доступ к {file_name} удалён."

                return f"⚠️ Доступ к {file_name} не найден."
            except Exception as e:
                return f"❌ Ошибка {file_name}: {str(e)[:100]}"

        results.append(remove_permission(FT_GOOGLE_SHEETS_ID, email, "таблице"))

        form_id = FT_GOOGLE_FORM_ID
        if "/d/" in form_id:
            form_id = form_id.split("/d/")[1].split("/")[0]
        elif "/e/" in form_id:
            form_id = form_id.split("/e/")[1].split("/")[0]

        if form_id:
            results.append(remove_permission(form_id, email, "форме"))
        else:
            results.append("❌ ID формы не указан.")

        embed = discord.Embed(
            title="🔒 Забрать доступ • FTstaff",
            color=discord.Color.green() if not any(r.startswith("❌") for r in results) else discord.Color.red(),
        )
        embed.add_field(name="📧 Email", value=email, inline=False)
        embed.add_field(name="📋 Результат", value="\n".join(results), inline=False)
        embed.set_footer(text=f"Забрал: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="выдатьбаллы", description="[FT] Выдать баллы сотруднику по нику")
@app_commands.describe(nick="Ник сотрудника", amount="Количество баллов")
async def add_points(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице FT.")
            return

        current_points = parse_points(user_data['points'])
        new_points = current_points + amount

        update_user(FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME, user_data['row'], 3, str(new_points))

        embed = discord.Embed(
            title="✅ Выдача баллов • FTstaff",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="💰 Выдано", value=f"**{amount}** баллов", inline=True)
        embed.add_field(name="📊 Итог", value=f"Было: **{current_points}** → Стало: **{new_points}**", inline=False)
        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="снятьбаллы", description="[FT] Снять баллы у сотрудника по нику")
@app_commands.describe(nick="Ник сотрудника", amount="Количество баллов")
async def remove_points(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице FT.")
            return

        current_points = parse_points(user_data['points'])
        new_points = current_points - amount

        if new_points < 0:
            new_points = 0

        update_user(FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME, user_data['row'], 3, str(new_points))

        embed = discord.Embed(
            title="✅ Снятие баллов • FTstaff",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="💰 Снято", value=f"**{amount}** баллов", inline=True)
        embed.add_field(name="📊 Итог", value=f"Было: **{current_points}** → Стало: **{new_points}**", inline=False)
        embed.set_footer(text=f"Снял: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="снятьварн", description="[FT] Снять 1 варн у сотрудника")
@app_commands.describe(nick="Ник сотрудника")
async def remove_warn(interaction: discord.Interaction, nick: str):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        user_data = find_user_by_nick(nick, FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице FT.")
            return

        sheet = get_sheet(FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warns = user_data.get('warns_count', 0)
        if current_warns <= 0:
            await interaction.followup.send(f"❌ У {nick} нет варнов для снятия.")
            return

        current_points = parse_points(user_data.get('points', '0'))

        if current_points < FT_WARN_COST:
            await interaction.followup.send(
                f"❌ Недостаточно баллов для снятия варна!\n"
                f"Требуется: **{FT_WARN_COST}** баллов\n"
                f"В наличии: **{current_points}** баллов"
            )
            return

        new_warns = current_warns - 1
        new_warns_str = f'{new_warns}/3'
        sheet.update_cell(row, 4, new_warns_str)

        new_points = current_points - FT_WARN_COST
        if new_points < 0:
            new_points = 0
        sheet.update_cell(row, 3, str(new_points))

        embed = discord.Embed(
            title="✅ Снятие варна • FTstaff",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="📋 Варны", value=f"{user_data.get('warns', '0/3')} → {new_warns_str}", inline=True)
        embed.add_field(name="💰 Списано", value=f"**{FT_WARN_COST}** баллов", inline=True)
        embed.add_field(name="💰 Остаток", value=f"**{new_points}** баллов", inline=False)
        embed.set_footer(text=f"Снял: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="снятьустник", description="[FT] Снять 1 устник у сотрудника")
@app_commands.describe(nick="Ник сотрудника")
async def remove_warning(interaction: discord.Interaction, nick: str):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        user_data = find_user_by_nick(nick, FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице FT.")
            return

        sheet = get_sheet(FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warnings = user_data.get('warnings_count', 0)
        if current_warnings <= 0:
            await interaction.followup.send(f"❌ У {nick} нет устников для снятия.")
            return

        current_points = parse_points(user_data.get('points', '0'))

        if current_points < FT_WARNING_COST:
            await interaction.followup.send(
                f"❌ Недостаточно баллов для снятия устника!\n"
                f"Требуется: **{FT_WARNING_COST}** баллов\n"
                f"В наличии: **{current_points}** баллов"
            )
            return

        new_warnings = current_warnings - 1
        new_warnings_str = f'{new_warnings}/3'
        sheet.update_cell(row, 5, new_warnings_str)

        new_points = current_points - FT_WARNING_COST
        if new_points < 0:
            new_points = 0
        sheet.update_cell(row, 3, str(new_points))

        embed = discord.Embed(
            title="✅ Снятие устника • FTstaff",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="📋 Устники", value=f"{user_data.get('warnings', '0/3')} → {new_warnings_str}", inline=True)
        embed.add_field(name="💰 Списано", value=f"**{FT_WARNING_COST}** баллов", inline=True)
        embed.add_field(name="💰 Остаток", value=f"**{new_points}** баллов", inline=False)
        embed.set_footer(text=f"Снял: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="stat", description="[FT] Показать статистику сотрудника по нику")
@app_commands.describe(nick="Ник сотрудника")
async def stat(interaction: discord.Interaction, nick: str):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        user_data = find_user_by_nick(nick, FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице FT.")
            return

        embed = discord.Embed(
            title=f"📊 Статистика {user_data['nick']} • FTstaff",
            color=discord.Color.blue()
        )
        embed.add_field(name="☘ Должность", value=user_data['position'], inline=True)
        embed.add_field(name="❀ Баллы", value=user_data['points'], inline=True)
        embed.add_field(name="☠ Варны", value=user_data['warns'], inline=True)
        embed.add_field(name="☠ Устники", value=user_data['warnings'], inline=True)
        embed.add_field(name="✉ Почта", value=user_data['email'] or 'Не указана', inline=True)
        embed.set_footer(text="Тг разработчика • @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="выдатьустник", description="[FT] Выдать устник сотруднику (3 устника = 1 варн)")
@app_commands.describe(nick="Ник сотрудника", amount="Количество устников (1-3)")
async def give_warning(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице FT.")
            return

        sheet = get_sheet(FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warnings = user_data.get('warnings_count', 0)
        current_warns = user_data.get('warns_count', 0)

        total_warnings = current_warnings + amount
        new_warns = current_warns
        new_warnings = total_warnings

        while new_warnings >= 3:
            new_warnings -= 3
            new_warns += 1

        if new_warns > 3:
            new_warns = 3

        new_warnings_str = f'{new_warnings}/3'
        new_warns_str = f'{new_warns}/3'

        sheet.update_cell(row, 5, new_warnings_str)
        sheet.update_cell(row, 4, new_warns_str)

        max_reached = []
        if new_warnings == 3:
            max_reached.append("устников 3/3")
        if new_warns == 3:
            max_reached.append("варнов 3/3")

        embed = discord.Embed(
            title="✅ Выдача устника • FTstaff",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="📋 Выдано устников", value=f"**{amount}**", inline=True)
        embed.add_field(
            name="📋 Устники",
            value=f"Было: {user_data.get('warnings', '0/3')} → Стало: **{new_warnings_str}**",
            inline=False
        )
        embed.add_field(
            name="☠ Варны",
            value=f"Было: {user_data.get('warns', '0/3')} → Стало: **{new_warns_str}**",
            inline=False
        )

        if max_reached:
            embed.add_field(
                name="⚠️ ВНИМАНИЕ",
                value=f"Достигнут максимум: {', '.join(max_reached)}!",
                inline=False
            )

        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="выдатьварн", description="[FT] Выдать варн сотруднику")
@app_commands.describe(nick="Ник сотрудника", amount="Количество варнов (1-3)")
async def give_warn(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из artytest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице FT.")
            return

        sheet = get_sheet(FT_GOOGLE_SHEETS_ID, FT_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warns = user_data.get('warns_count', 0)

        new_warns = current_warns + amount

        if new_warns > 3:
            new_warns = 3

        new_warns_str = f'{new_warns}/3'

        sheet.update_cell(row, 4, new_warns_str)

        embed = discord.Embed(
            title="✅ Выдача варна • FTstaff",
            color=discord.Color.red()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="☠ Выдано варнов", value=f"**{amount}**", inline=True)
        embed.add_field(
            name="☠ Варны",
            value=f"Было: {user_data.get('warns', '0/3')} → Стало: **{new_warns_str}**",
            inline=False
        )

        if new_warns == 3:
            embed.add_field(
                name="⚠️ ВНИМАНИЕ",
                value="Достигнут максимум: варнов 3/3!",
                inline=False
            )

        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


# =========================================================
# КОМАНДЫ RW (rwtest-main) - С ПРЕФИКСОМ 'rw'
# =========================================================

@bot.tree.command(name="выдатьдоступrw", description="[RW] Выдать доступ к таблице и форме по email")
@app_commands.describe(email="Email пользователя", nick="Ник сотрудника (кому выдаётся доступ)")
async def grant_access_rw(interaction: discord.Interaction, email: str, nick: str):
    # Логика из rwtest-main
    try:
        await interaction.response.defer()

        email = email.strip().lower()
        nick = nick.strip()

        if not email or '@' not in email:
            await interaction.followup.send("❌ Укажите корректный email.")
            return

        if not nick:
            await interaction.followup.send("❌ Укажите ник сотрудника.")
            return

        service = get_google_service()
        if not service:
            await interaction.followup.send("❌ Ошибка подключения к Google API.")
            return

        results = []

        try:
            service.permissions().create(
                fileId=RW_GOOGLE_SHEETS_ID,
                body={"type": "user", "role": "reader", "emailAddress": email},
                sendNotificationEmail=True
            ).execute()
            results.append("✅ Доступ к таблице выдан.")
        except Exception as e:
            if "already exists" in str(e).lower():
                results.append("⚠️ Доступ к таблице уже был выдан.")
            else:
                results.append(f"❌ Ошибка таблицы: {str(e)[:100]}")

        # Парсинг ID формы RW (идентичная логика FT)
        form_id = RW_GOOGLE_FORM_ID
        if form_id:
            # Извлекаем ID из URL, если это URL
            if "/d/" in form_id:
                form_id = form_id.split("/d/")[1].split("/")[0]
            elif "/e/" in form_id:
                form_id = form_id.split("/e/")[1].split("/")[0]
            # Если это уже чистый ID - используем как есть

            try:
                service.permissions().create(
                    fileId=form_id,
                    body={"type": "user", "role": "reader", "emailAddress": email, "view": "published"},
                    sendNotificationEmail=True
                ).execute()
                results.append("✅ Доступ к форме выдан.")
            except Exception as e:
                error_str = str(e).lower()
                if "already exists" in error_str:
                    results.append("⚠️ Доступ к форме уже был выдан.")
                elif "404" in error_str or "not found" in error_str:
                    results.append("⚠️ Форма RW не найдена или недоступна (ID может быть неверным). Доступ к таблице выдан.")
                else:
                    results.append(f"❌ Ошибка формы: {str(e)[:100]}")
        else:
            results.append("❌ ID формы не указан.")

        embed = discord.Embed(
            title="🔑 Выдача доступа • RWstaff",
            color=discord.Color.green() if not any(r.startswith("❌") for r in results) else discord.Color.red(),
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="📧 Email", value=email, inline=True)
        embed.add_field(name="📋 Результат", value="\n".join(results), inline=False)
        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="забратьдоступrw", description="[RW] Забрать доступ к таблице и форме по email")
@app_commands.describe(email="Email пользователя")
async def revoke_access_rw(interaction: discord.Interaction, email: str):
    # Логика из rwtest-main (расширенная версия с published view)
    try:
        await interaction.response.defer()

        email = email.strip().lower()

        if not email or '@' not in email:
            await interaction.followup.send("❌ Укажите корректный email.")
            return

        service = get_google_service()
        if not service:
            await interaction.followup.send("❌ Ошибка подключения к Google API.")
            return

        results = []

        def remove_permission(file_id, email, file_name):
            try:
                # Обычные разрешения
                permissions = service.permissions().list(
                    fileId=file_id,
                    fields="permissions(id, emailAddress, type, role, view)",
                    supportsAllDrives=True
                ).execute()

                perms_list = permissions.get('permissions', [])

                # Если нужного email нет — проверяем published view
                if not any(
                    p.get('type') == 'user' and p.get('emailAddress', '').lower() == email
                    for p in perms_list
                ):
                    try:
                        permissions = service.permissions().list(
                            fileId=file_id,
                            fields="permissions(id, emailAddress, type, role, view)",
                            includePermissionsForView="published",
                            supportsAllDrives=True
                        ).execute()
                        perms_list = permissions.get('permissions', [])
                    except Exception as e:
                        print(f"⚠️ published view недоступен: {e}")

                # Удаляем
                for perm in perms_list:
                    if perm.get('type') == 'user' and perm.get('emailAddress', '').lower() == email:
                        service.permissions().delete(
                            fileId=file_id,
                            permissionId=perm['id'],
                            supportsAllDrives=True
                        ).execute()
                        return f"✅ Доступ к {file_name} удалён."

                return f"⚠️ Доступ к {file_name} не найден (проверьте, что email совпадает)."
            except Exception as e:
                return f"❌ Ошибка {file_name}: {str(e)[:150]}"

        # Таблица
        results.append(remove_permission(RW_GOOGLE_SHEETS_ID, email, "таблице"))

        # Форма
        form_id = RW_GOOGLE_FORM_ID.strip()
        if form_id:
            results.append(remove_permission(form_id, email, "форме"))
        else:
            results.append("❌ ID формы не указан.")

        embed = discord.Embed(
            title="🔒 Забрать доступ • RWstaff",
            color=discord.Color.green() if not any(r.startswith("❌") for r in results) else discord.Color.red(),
        )
        embed.add_field(name="📧 Email", value=email, inline=False)
        embed.add_field(name="📋 Результат", value="\n".join(results), inline=False)
        embed.set_footer(text=f"Забрал: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="выдатьбаллыrw", description="[RW] Выдать баллы сотруднику по нику")
@app_commands.describe(nick="Ник сотрудника", amount="Количество баллов")
async def add_points_rw(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из rwtest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.")
            return

        current_points = parse_points(user_data['points'])
        new_points = current_points + amount

        update_user(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME, user_data['row'], 3, str(new_points))

        embed = discord.Embed(
            title="✅ Выдача баллов • RWstaff",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="💰 Выдано", value=f"**{amount}** баллов", inline=True)
        embed.add_field(name="📊 Итог", value=f"Было: **{current_points}** → Стало: **{new_points}**", inline=False)
        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="снятьбаллыrw", description="[RW] Снять баллы у сотрудника по нику")
@app_commands.describe(nick="Ник сотрудника", amount="Количество баллов")
async def remove_points_rw(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из rwtest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.")
            return

        current_points = parse_points(user_data['points'])
        new_points = current_points - amount

        if new_points < 0:
            new_points = 0

        update_user(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME, user_data['row'], 3, str(new_points))

        embed = discord.Embed(
            title="✅ Снятие баллов • RWstaff",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Сотрудник", value=nick, inline=True)
        embed.add_field(name="💰 Снято", value=f"**{amount}** баллов", inline=True)
        embed.add_field(name="📊 Итог", value=f"Было: **{current_points}** → Стало: **{new_points}**", inline=False)
        embed.set_footer(text=f"Снял: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="снятьварнrw", description="[RW] Снять 1 варн у сотрудника")
@app_commands.describe(nick="Ник сотрудника")
async def remove_warn_rw(interaction: discord.Interaction, nick: str):
    # Логика из rwtest-main (с улучшенным поиском)
    try:
        await interaction.response.defer()

        user_data = find_user_by_nick(nick, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)

        if not user_data:
            # Пробуем найти с другим вариантом поиска
            sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
            if sheet:
                values = sheet.col_values(1)
                found = False
                for row_num, value in enumerate(values, start=1):
                    if nick.strip().lower() in value.lower():
                        user_data = find_user_by_nick(value, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
                        found = True
                        break
                if not found:
                    await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.\nПроверьте, как записан ник в таблице.")
                    return
            else:
                await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.")
                return

        sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warns = user_data.get('warns_count', 0)
        if current_warns <= 0:
            await interaction.followup.send(f"❌ У {nick} нет варнов для снятия.")
            return

        current_points = parse_points(user_data.get('points', '0'))

        if current_points < RW_WARN_COST:
            await interaction.followup.send(
                f"❌ Недостаточно баллов для снятия варна!\n"
                f"Требуется: **{RW_WARN_COST}** баллов\n"
                f"В наличии: **{current_points}** баллов"
            )
            return

        new_warns = current_warns - 1
        new_warns_str = f'{new_warns}/3'
        sheet.update_cell(row, 4, new_warns_str)

        new_points = current_points - RW_WARN_COST
        if new_points < 0:
            new_points = 0
        sheet.update_cell(row, 3, str(new_points))

        embed = discord.Embed(
            title="✅ Снятие варна • RWstaff",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Сотрудник", value=user_data['nick'], inline=True)
        embed.add_field(name="📋 Варны", value=f"{user_data.get('warns', '0/3')} → {new_warns_str}", inline=True)
        embed.add_field(name="💰 Списано", value=f"**{RW_WARN_COST}** баллов", inline=True)
        embed.add_field(name="💰 Остаток", value=f"**{new_points}** баллов", inline=False)
        embed.set_footer(text=f"Снял: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="снятьустникrw", description="[RW] Снять 1 устник у сотрудника")
@app_commands.describe(nick="Ник сотрудника")
async def remove_warning_rw(interaction: discord.Interaction, nick: str):
    # Логика из rwtest-main (с улучшенным поиском)
    try:
        await interaction.response.defer()

        user_data = find_user_by_nick(nick, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)

        if not user_data:
            sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
            if sheet:
                values = sheet.col_values(1)
                for row_num, value in enumerate(values, start=1):
                    if nick.strip().lower() in value.lower():
                        user_data = find_user_by_nick(value, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
                        break
                if not user_data:
                    await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.\nПроверьте, как записан ник в таблице.")
                    return
            else:
                await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.")
                return

        sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warnings = user_data.get('warnings_count', 0)
        if current_warnings <= 0:
            await interaction.followup.send(f"❌ У {nick} нет устников для снятия.")
            return

        current_points = parse_points(user_data.get('points', '0'))

        if current_points < RW_WARNING_COST:
            await interaction.followup.send(
                f"❌ Недостаточно баллов для снятия устника!\n"
                f"Требуется: **{RW_WARNING_COST}** баллов\n"
                f"В наличии: **{current_points}** баллов"
            )
            return

        new_warnings = current_warnings - 1
        new_warnings_str = f'{new_warnings}/3'
        sheet.update_cell(row, 5, new_warnings_str)

        new_points = current_points - RW_WARNING_COST
        if new_points < 0:
            new_points = 0
        sheet.update_cell(row, 3, str(new_points))

        embed = discord.Embed(
            title="✅ Снятие устника • RWstaff",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Сотрудник", value=user_data['nick'], inline=True)
        embed.add_field(name="📋 Устники", value=f"{user_data.get('warnings', '0/3')} → {new_warnings_str}", inline=True)
        embed.add_field(name="💰 Списано", value=f"**{RW_WARNING_COST}** баллов", inline=True)
        embed.add_field(name="💰 Остаток", value=f"**{new_points}** баллов", inline=False)
        embed.set_footer(text=f"Снял: {interaction.user.display_name} • Тг разработчика @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="statrw", description="[RW] Показать статистику сотрудника по нику")
@app_commands.describe(nick="Ник сотрудника")
async def stat_rw(interaction: discord.Interaction, nick: str):
    # Логика из rwtest-main
    try:
        await interaction.response.defer()

        user_data = find_user_by_nick(nick, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)

        if not user_data:
            await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.")
            return

        embed = discord.Embed(
            title=f"📊 Статистика {user_data['nick']} • RWstaff",
            color=discord.Color.purple()
        )
        embed.add_field(name="☘ Должность", value=user_data['position'], inline=True)
        embed.add_field(name="❀ Баллы", value=user_data['points'], inline=True)
        embed.add_field(name="☠ Варны", value=user_data['warns'], inline=True)
        embed.add_field(name="☠ Устники", value=user_data['warnings'], inline=True)
        embed.add_field(name="✉ Почта", value=user_data['email'] or 'Не указана', inline=True)
        embed.set_footer(text="Тг разработчика • @svets1337")

        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="выдатьустникrw", description="[RW] Выдать устник сотруднику (3 устника = 1 варн)")
@app_commands.describe(nick="Ник сотрудника", amount="Количество устников")
async def give_warning_rw(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из rwtest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)

        if not user_data:
            sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
            if sheet:
                values = sheet.col_values(1)
                for row_num, value in enumerate(values, start=1):
                    if nick.strip().lower() in value.lower():
                        user_data = find_user_by_nick(value, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
                        break
                if not user_data:
                    await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.\nПроверьте, как записан ник в таблице.")
                    return
            else:
                await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.")
                return

        sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warnings = user_data.get('warnings_count', 0)
        current_warns = user_data.get('warns_count', 0)

        total_warnings = current_warnings + amount
        new_warns = current_warns
        new_warnings = total_warnings

        # 3 устника = 1 варн
        while new_warnings >= 3:
            new_warnings -= 3
            new_warns += 1

        # Максимум 3 варна
        if new_warns > 3:
            new_warns = 3

        new_warnings_str = f'{new_warnings}/3'
        new_warns_str = f'{new_warns}/3'

        # Столбец E (5) — устники, столбец D (4) — варны
        sheet.update_cell(row, 5, new_warnings_str)
        sheet.update_cell(row, 4, new_warns_str)

        max_reached = []
        if new_warnings == 3:
            max_reached.append("устников 3/3")
        if new_warns == 3:
            max_reached.append("варнов 3/3")

        embed = discord.Embed(
            title="✅ Выдача устника • RWstaff",
            color=discord.Color.orange()
        )
        embed.add_field(name="👤 Сотрудник", value=user_data['nick'], inline=True)
        embed.add_field(name="📋 Выдано устников", value=f"**{amount}**", inline=True)
        embed.add_field(
            name="📋 Устники",
            value=f"Было: {user_data.get('warnings', '0/3')} → Стало: **{new_warnings_str}**",
            inline=False
        )
        embed.add_field(
            name="☠ Варны",
            value=f"Было: {user_data.get('warns', '0/3')} → Стало: **{new_warns_str}**",
            inline=False
        )

        if max_reached:
            embed.add_field(
                name="⚠️ ВНИМАНИЕ",
                value=f"Достигнут максимум: {', '.join(max_reached)}!",
                inline=False
            )

        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


@bot.tree.command(name="выдатьварнrw", description="[RW] Выдать варн сотруднику")
@app_commands.describe(nick="Ник сотрудника", amount="Количество варнов")
async def give_warn_rw(interaction: discord.Interaction, nick: str, amount: int):
    # Логика из rwtest-main
    try:
        await interaction.response.defer()

        if amount <= 0:
            await interaction.followup.send("❌ Количество должно быть больше 0.")
            return

        user_data = find_user_by_nick(nick, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)

        if not user_data:
            sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
            if sheet:
                values = sheet.col_values(1)
                for row_num, value in enumerate(values, start=1):
                    if nick.strip().lower() in value.lower():
                        user_data = find_user_by_nick(value, RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
                        break
                if not user_data:
                    await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.\nПроверьте, как записан ник в таблице.")
                    return
            else:
                await interaction.followup.send(f"❌ Сотрудник '{nick}' не найден в таблице RW.")
                return

        sheet = get_sheet(RW_GOOGLE_SHEETS_ID, RW_SHEET_NAME)
        if not sheet:
            await interaction.followup.send("❌ Ошибка подключения к таблице.")
            return

        row = user_data['row']

        current_warns = user_data.get('warns_count', 0)
        new_warns = current_warns + amount

        # Максимум 3 варна
        if new_warns > 3:
            new_warns = 3

        new_warns_str = f'{new_warns}/3'

        # Столбец D (4) — варны
        sheet.update_cell(row, 4, new_warns_str)

        embed = discord.Embed(
            title="✅ Выдача варна • RWstaff",
            color=discord.Color.red()
        )
        embed.add_field(name="👤 Сотрудник", value=user_data['nick'], inline=True)
        embed.add_field(name="☠ Выдано варнов", value=f"**{amount}**", inline=True)
        embed.add_field(
            name="☠ Варны",
            value=f"Было: {user_data.get('warns', '0/3')} → Стало: **{new_warns_str}**",
            inline=False
        )

        if new_warns == 3:
            embed.add_field(
                name="⚠️ ВНИМАНИЕ",
                value="Достигнут максимум: варнов 3/3!",
                inline=False
            )

        embed.set_footer(text=f"Выдал: {interaction.user.display_name} • Тг разработчика @svets1337")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Ошибка: {e}")


# =========================================================
# ОБЩИЕ КОМАНДЫ
# =========================================================



# =========================================================
# ЗАПУСК
# =========================================================

@bot.event
async def on_ready():
    print(f'✅ Merged Staff Bot {bot.user} запущен!')
    print(f'✅ FT таблица: {FT_SHEET_NAME}')
    print(f'✅ RW таблица: {RW_SHEET_NAME}')
    await bot.tree.sync()
    print('✅ Команды синхронизированы')


if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
