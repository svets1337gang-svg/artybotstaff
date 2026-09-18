# Merged Staff Bot

Discord bot for managing staff across multiple systems (FT, RW).

## Features

- Staff point management (grant/revoke)
- Warnings and strikes system (3 strikes = 1 warning)
- Google Sheets integration
- Health check web server

## Project Structure

```
merged-staff/
├── bot.py              # Main bot code (FT + RW commands)
├── config.py           # Configuration (FT/RW settings)
├── web.py              # Flask web server for healthchecks
├── requirements.txt    # Python dependencies
├── credentials.json    # Google Service Account (env variable)
└── .env                # Environment variables
```

## Environment Variables

Required in `.env` or Render environment:

```env
# Discord
DISCORD_TOKEN=your_discord_bot_token

# FT Settings
FT_GOOGLE_SHEETS_ID=your_ft_sheet_id
FT_SHEET_NAME=Состав FT
FT_GOOGLE_FORM_ID=your_ft_form_id

# RW Settings
RW_GOOGLE_SHEETS_ID=your_rw_sheet_id
RW_SHEET_NAME=Состав RW
RW_GOOGLE_FORM_ID=your_rw_form_id

# Prices (FT)
FT_WARN_COST=500
FT_WARNING_COST=175
FT_VACATION_COST=100

# Prices (RW)
RW_WARN_COST=1000
RW_WARNING_COST=350
RW_VACATION_COST=200

# Optional
PORT=10000
```

### Google Credentials

Place `credentials.json` (Google Service Account) in the project root.

## Deployment to Render

1. Create a Web Service on Render
2. Set **Build Command**: `pip install -r requirements.txt`
3. Set **Start Command**: `python web.py`
4. Add all environment variables from `.env`
5. Upload `credentials.json` via environment variable or secure file

## Commands

### FT Commands (no prefix)
- `/help` - Show all commands
- `/stat ник` - Staff statistics
- `/выдатьбаллы ник кол-во` - Grant points
- `/снятьбаллы ник кол-во` - Remove points
- `/выдатьварн ник кол-во` - Issue warning
- `/снятьварн ник` - Remove warning (costs points)
- `/выдатьустник ник кол-во` - Issue strike
- `/снятьустник ник` - Remove strike (costs points)
- `/выдатьдоступ email ник` - Grant sheet access
- `/забратьдоступ email` - Revoke access

### RW Commands (suffix `rw`)
- `/helprw` - Show all commands
- `/statrw ник` - Staff statistics
- `/выдатьбаллыrw ник кол-во` - Grant points
- `/снятьбаллыrw ник кол-во` - Remove points
- `/выдатьварнrw ник кол-во` - Issue warning
- `/снятьварнrw ник` - Remove warning
- `/выдатьустникrw ник кол-во` - Issue strike
- `/снятьустникrw ник` - Remove strike
- `/выдатьдоступrw email ник` - Grant sheet access
- `/забратьдоступrw email` - Revoke access

## Web Server Endpoints

- `/` - Health check (returns "OK")
- `/ping` - Returns "pong"

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run bot only
python bot.py

# Run with web server
python web.py
```

---

**Developer**: @svets1337 (Telegram)
