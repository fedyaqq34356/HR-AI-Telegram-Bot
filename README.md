# AI Recruitment Telegram Bot

A sophisticated Telegram bot designed for recruitment agencies working with streaming platforms. Features AI-powered responses, automated application processing, photo review, OCR for ID extraction, and comprehensive admin panel.

> **Note**: This bot is specifically designed for agencies recruiting models for the Halo streaming application.

## 🌟 Features

### User Features
- **AI-Powered Chat**: Intelligent responses using g4f (GPT-4 Free) with automatic FAQ matching
- **Smart Photo Handling**: Supports both single and grouped photo uploads
- **Application Process**: Streamlined multi-step registration workflow
- **Review System**: Built-in review image gallery for social proof
- **Multilingual Support**: Russian/Ukrainian interface with natural conversation flow

### Admin Features
- **Smart Dashboard**: Real-time statistics and AI efficiency metrics
- **Application Review**: Review candidate photos and information with approve/reject workflow
- **Conversation Monitoring**: View all user conversations and export chat history
- **AI Training**: Manual answers are automatically learned by the AI
- **Settings Management**: Customize welcome messages, rejection/approval templates
- **Forbidden Topics**: Configure topics that should escalate to admin
- **Logs Export**: Download bot logs for debugging

### Technical Features
- **OCR Integration**: Automatic ID extraction from screenshots using Tesseract
- **State Management**: FSM (Finite State Machine) for user flow control
- **Database**: SQLite with aiosqlite for async operations
- **AI Confidence Scoring**: Automatic escalation for low-confidence responses
- **Media Group Support**: Proper handling of grouped photo uploads
- **Retry Logic**: Robust AI request handling with fallback

## 📋 Requirements

- Python 3.8+
- Telegram Bot Token
- Tesseract OCR (for ID extraction)

## 🚀 Installation

### 1. Clone the repository

```bash
git clone https://github.com/fedyaqq34356/HR-AI-Telegram-Bot.git
cd ai-recruitment-bot
```

### 2. Create virtual environment

```bash
python -m venv venv
```

### 3. Activate virtual environment

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Install Tesseract OCR

**Windows:**
- Download installer from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- Install to default location or update path in `utils/ocr_handler.py`

**macOS:**
```bash
brew install tesseract
```

**Linux:**
```bash
sudo apt-get install tesseract-ocr
```

### 6. Configure environment variables

Create a `.env` file in the project root:

```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_ID=your_telegram_user_id_here
```

### 7. Setup review images (optional)

Create a `goods` folder and add review images:

```bash
mkdir goods
# Add your review images named: review_testimonial_1.jpg, review_success_2.jpg, etc.
```

### 8. Setup screenshot example

Create an `images` folder and add registration guide:

```bash
mkdir images
# Add halo_download.jpg with app download screenshot
```

## 📱 Getting Started

### Get Your Bot Token

1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token
4. Paste it into `.env` file

### Get Your Admin ID

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Copy your user ID
3. Paste it into `.env` file as `ADMIN_ID`

### Run the Bot

```bash
python main.py
```

The bot will:
- Initialize the database
- Load FAQ and settings
- Start listening for messages
- Log all activity to `bot.log`

To stop the bot, press `Ctrl+C`.

## 🎯 Usage

### For Candidates

1. Start the bot with `/start`
2. Read the welcome message
3. Ask questions (AI will answer automatically)
4. Send 2-3 photos when ready
5. Answer work hours and experience questions
6. Wait for admin review
7. If approved, receive registration instructions
8. Send screenshot with ID
9. Account will be activated next business day

### For Admins

1. Send `/admin` to access admin panel
2. View statistics and monitor AI efficiency
3. Review applications (approve/reject)
4. Answer questions that AI escalated
5. Export conversations or logs
6. Customize messages and settings

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from BotFather | Yes |
| `ADMIN_ID` | Telegram user ID of admin | Yes |

### Customizable Settings

Edit `config.py` to customize:

- `PHOTOS_MIN` - Minimum photos required (default: 2)
- `PHOTOS_MAX` - Maximum photos allowed (default: 3)
- `AI_CONFIDENCE_THRESHOLD` - Minimum confidence for auto-response (default: 70)
- `FORBIDDEN_TOPICS` - Topics that trigger universal response
- `UNIVERSAL_RESPONSE` - Response for forbidden topics

### AI Behavior

Edit `SYSTEM_PROMPT` in `config.py` to customize:
- AI personality and tone
- Response style and format
- When to escalate to admin
- JSON response structure

## 📊 Database Schema

The bot uses SQLite with the following tables:

- `users` - User profiles and status tracking
- `messages` - Conversation history
- `photos` - Uploaded photo file IDs
- `applications` - Job applications
- `faq` - Frequently asked questions
- `ai_learning` - AI training data from admin answers
- `settings` - Bot configuration
- `forbidden_topics` - Restricted conversation topics
- `pending_questions` - Questions waiting for admin response

## 🤖 AI System

The bot uses a multi-layer AI system:

1. **Direct FAQ Matching** - Instant answers for common questions
2. **AI Context Building** - Uses conversation history and learned answers
3. **Confidence Scoring** - AI rates its own confidence (0-100)
4. **Auto Escalation** - Low confidence questions go to admin
5. **Learning System** - Admin answers are stored and reused

### AI Provider

Uses [g4f](https://github.com/xtekky/gpt4free) (GPT-4 Free) with retry provider for reliability.

## 📁 Project Structure

```
ai-recruitment-bot/
├── main.py                 # Entry point
├── config.py              # Configuration
├── states.py              # FSM states
├── keyboards.py           # Telegram keyboards
├── database/              # Database modules
│   ├── __init__.py
│   ├── core.py           # DB initialization
│   ├── users.py          # User operations
│   ├── messages.py       # Message storage
│   ├── photos.py         # Photo storage
│   ├── applications.py   # Application management
│   ├── faq.py           # FAQ management
│   ├── ai_learning.py   # AI training data
│   ├── settings.py      # Settings storage
│   └── forbidden.py     # Forbidden topics
├── handlers/             # Message handlers
│   ├── __init__.py
│   ├── user.py          # User interactions
│   ├── admin.py         # Admin panel
│   ├── approval.py      # Application review
│   ├── screenshot.py    # Screenshot processing
│   └── reviews.py       # Review system
├── utils/               # Utilities
│   ├── ai_handler.py   # AI integration
│   └── ocr_handler.py  # OCR for ID extraction
├── images/             # Bot images
│   └── halo_download.jpg
├── goods/              # Review images
│   └── review_*.jpg
├── requirements.txt    # Dependencies
├── .env               # Environment variables
├── bot.db            # SQLite database
├── bot.log           # Application logs
└── README.md         # This file
```

## 🔧 Troubleshooting

### Bot doesn't respond

- Check `BOT_TOKEN` is correct
- Ensure bot is running (`python main.py`)
- Check `bot.log` for errors

### AI not working

- g4f may experience downtime (it's free)
- Check internet connection
- Questions will escalate to admin automatically

### OCR not extracting ID

- Ensure Tesseract is installed
- Check Tesseract path in `utils/ocr_handler.py`
- User can manually type ID as fallback

### Database errors

- Delete `bot.db` and restart (data will be lost)
- Check SQLite is available
- Ensure write permissions

### Photos not uploading

- Check Telegram file size limits (20MB)
- Ensure user is in correct state
- Verify database is working

## 🌐 Adapting for Other Use Cases

This bot can be adapted for various recruitment scenarios:

1. **Change Industry**: Modify welcome message and FAQ in `database/faq.py`
2. **Adjust Workflow**: Customize states in `states.py` and handlers
3. **Modify Questions**: Update application questions in `handlers/user.py`
4. **Change Language**: Translate all strings in relevant files
5. **Add Features**: Extend handlers and database as needed

## 📝 License

This project is licensed under the GNU GENERAL PUBLIC LICENSE - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Disclaimer

This bot uses g4f (GPT-4 Free) which may have availability issues. For production use, consider using official OpenAI API or Anthropic Claude API.

## 📧 Support

For issues, questions, or suggestions, please open an issue on GitHub.

---

**Built with Python, Aiogram, and g4f**