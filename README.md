# 🧩 Puzzle Chat AI

A real-time collaborative puzzle-solving chat application where teams work together with AI assistance to solve challenging puzzles and riddles.

## 🎯 What This Project Does

**Puzzle Chat AI** brings people together to solve puzzles collaboratively in real-time. Users can:

- 💬 **Chat in real-time** with other puzzle solvers
- 🤖 **Get AI assistance** from integrated ChatGPT for hints and suggestions  
- 🧩 **Solve puzzles together** in shared virtual rooms
- 📊 **Track progress** with conversation summaries and interaction logs
- 👥 **Collaborate seamlessly** with WebSocket-powered live updates

Perfect for puzzle enthusiasts, team building activities, educational settings, or anyone who enjoys collaborative problem-solving!

## 🛠️ Tech Stack

- **Backend**: Django + Django Channels for WebSocket support
- **Database**: PostgreSQL 
- **AI Integration**: OpenAI GPT API
- **Real-time Communication**: WebSockets
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Can be deployed with ngrok for testing or any WSGI server

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL
- OpenAI API key

### 1. Clone and Setup

```bash
git clone https://github.com/leowang3268/puzzle-chat-ai.git
cd puzzle-chat-ai
cd puzzle_chat_ai
```

### 2. Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Or install individually:
pip install django channels channels-redis
pip install openai psycopg2-binary
pip install python-dotenv redis django-redis
```

### 3. Environment Configuration

```bash
# Copy the example environment file
cp puzzle_chat_ai/.env.example puzzle_chat_ai/.env

# Edit .env with your actual values:
# - Add your OpenAI API key
# - Configure database credentials
```

### 4. Database & Redis Setup

```bash
# Create PostgreSQL database
createdb puzzle_chat_ai

# Start Redis (for caching and real-time features)
# On macOS: brew services start redis
# On Ubuntu: sudo systemctl start redis
# On Windows: Download and run Redis

# Run migrations
python manage.py makemigrations
python manage.py migrate
```

### 5. Run the Application

```bash
python manage.py runserver
```

Visit `http://localhost:8000` to start solving puzzles!

## 🏗️ Project Structure

```
puzzle_chat_ai/
├── puzzle_chat_ai/          # Django project settings
│   ├── settings.py          # Main configuration
│   ├── asgi.py             # ASGI config for WebSockets
│   └── .env.example        # Environment template
├── chat/                   # Main chat application
│   ├── models.py           # Database models
│   ├── consumers.py        # WebSocket handlers
│   ├── views.py            # HTTP views
│   ├── templates/          # HTML templates
│   └── management/         # Custom Django commands
├── static/                 # CSS, JS files
└── requirements.txt        # Python dependencies
```

## 🔧 Key Features

### Real-time Chat
- Live messaging between users in puzzle rooms
- Message reactions and replies
- Typing indicators

### AI Integration
- Smart puzzle hints from ChatGPT with caching
- Conversation summaries
- Adaptive responses based on puzzle context
- Optimized API calls with fallback models

### Room Management
- Create and join puzzle rooms
- Room-specific chat history
- Export conversation data

### Data Management
- PostgreSQL for reliable data storage
- Export tools for chat logs
- Room cleanup utilities

## 🌐 Deployment with ngrok (for testing)

For sharing your local development with others:

```bash
# Install ngrok from https://ngrok.com/
# Run your Django server
python manage.py runserver

# In another terminal, expose it
ngrok http 8000

# Share the ngrok URL with collaborators
```

## 🤝 Contributing

We welcome contributions! Here's how to get started:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Commit your changes (`git commit -m 'Add amazing feature'`)
5. Push to the branch (`git push origin feature/amazing-feature`)
6. Open a Pull Request

## 📝 Environment Variables

Required environment variables (see `.env.example`):

```env
# Generate with: python generate_secret_key.py
SECRET_KEY=your_secret_key_here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
OPENAI_API_KEY=your_openai_api_key_here
DB_NAME=puzzle_chat_ai
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379
```

### 🔐 Security Setup

**Generate a secure secret key:**
```bash
python generate_secret_key.py
```

**For production deployment:**
- Use `.env.production.example` as template
- Set `DEBUG=False`
- Configure specific `ALLOWED_HOSTS`
- Use strong database passwords
- Never commit real `.env` files to git

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
- Ensure PostgreSQL is running
- Check database credentials in `.env`
- Verify database exists

**WebSocket Connection Failed**
- Check if Django Channels is properly installed
- Ensure ASGI application is configured correctly

**AI Responses Not Working**
- Verify OpenAI API key is valid
- Check API rate limits and billing

## 📄 License

This project is open source. Feel free to use and modify for your needs.

## 🙋‍♂️ Support

Having issues? Please:
1. Check the troubleshooting section above
2. Search existing GitHub issues
3. Create a new issue with detailed description

---

**Happy puzzle solving! 🧩✨**