# 🎵 Telegram Music Bot

A comprehensive Telegram bot for music recognition, artist information, track details, and music charts using ShazamIO, Last.fm, and Spotify APIs.

## ✨ Features

### 🔎 Music Recognition
- **Track Recognition**: Send audio files (voice messages, audio files, video notes) for instant song identification
- **Detailed Track Info**: Get comprehensive information about recognized tracks

### 👨‍🎤 Artist & Track Information  
- **Artist Details**: Biography, listener count, play statistics
- **Track Information**: Album, release date, duration, play counts
- **Listening Statistics**: Total plays, listener count, average plays per listener

### 🔍 Search Functionality
- **Artist Search**: Find artists by name with detailed results
- **Track Search**: Search for songs with comprehensive metadata
- **Similar Songs**: Discover music similar to your favorite tracks

### 📊 Charts & Top Lists
- **Top Artist Tracks**: Get the most popular songs by any artist
- **City Charts**: Top tracks in specific cities (regional approximation)
- **Country Charts**: Popular music by country
- **Genre Charts**: Top tracks by genre (worldwide and by country)
- **Global Charts**: Current worldwide trending music

## 🚀 Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository_url>
cd telegram-music-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Get API Keys

#### Telegram Bot Token (Required)
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` command and follow instructions
3. Copy the bot token

#### Last.fm API (Optional - Enhanced Features)
1. Visit [Last.fm API](https://www.last.fm/api/account/create)
2. Create an account and get API key + secret
3. Provides: Track statistics, similar songs, detailed charts

#### Spotify API (Optional - Additional Music Data)
1. Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create an app and get Client ID + Client Secret  
3. Provides: Enhanced recommendations, additional track metadata

### 4. Configure Environment
```bash
cp .env.example .env
```

Edit `.env` with your API keys:
```bash
# Required
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Optional (but recommended for full functionality)
LASTFM_API_KEY=your_lastfm_api_key_here
LASTFM_API_SECRET=your_lastfm_api_secret_here
SPOTIFY_CLIENT_ID=your_spotify_client_id_here
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret_here
```

### 5. Run the Bot
```bash
python music_bot.py
```

## 🎯 Usage

### Commands

#### 🔎 Recognition & Info
- Send any audio file → Automatic track recognition
- `/artist <artist_name>` → Artist information
- `/track <artist> - <song>` → Track details  
- `/listens <artist> - <song>` → Listening statistics

#### 🔍 Search
- `/search_artist <name>` → Find artists
- `/search_track <query>` → Search tracks
- `/similar <artist> - <song>` → Similar songs

#### 📊 Charts & Rankings
- `/top_artist <artist_name>` → Artist's top tracks
- `/top_city <city_name>` → City's popular music
- `/top_country <country_name>` → Country charts
- `/top_country_genre <country> <genre>` → Genre charts by country
- `/top_genre <genre>` → Global genre charts
- `/top_world` → Worldwide trending tracks

#### ℹ️ Help
- `/start` → Welcome message
- `/help` → Command list

### Example Usage

**Track Recognition:**
1. Record a voice message with music playing
2. Send it to the bot
3. Get instant track identification with interactive buttons

**Search Example:**
```
/artist Taylor Swift
/track Beatles - Hey Jude
/search_track bohemian rhapsody
/similar Radiohead - Creep
```

**Charts Example:**
```
/top_artist Eminem
/top_country USA
/top_genre rock
/top_country_genre UK electronic
```

## 🎵 Supported Audio Formats

- **Voice Messages** (.ogg, .mp3)
- **Audio Files** (.mp3, .wav, .flac, .m4a)
- **Video Notes** (circular video messages)

## 🌍 Supported Regions

**Countries:** USA, UK, Germany, France, Italy, Spain, Canada, Australia, Japan, Brazil, Russia, India, China, South Korea

**Genres:** rock, pop, hip-hop, electronic, jazz, classical, country, r&b, indie, metal, folk, blues, reggae, punk, alternative

## 🛠️ Technical Features

- **Async/Await**: High-performance asynchronous operations
- **Error Handling**: Comprehensive error management with user feedback
- **Interactive Buttons**: Telegram inline keyboards for better UX
- **Multi-API Integration**: ShazamIO, Last.fm, and Spotify for comprehensive data
- **File Management**: Automatic cleanup of temporary audio files
- **Logging**: Detailed logging for debugging and monitoring

## 📋 Dependencies

- `python-telegram-bot` - Telegram Bot API
- `shazamio` - Music recognition via Shazam
- `pylast` - Last.fm API integration
- `spotipy` - Spotify Web API
- `python-dotenv` - Environment variable management
- `aiohttp` - Async HTTP client
- `aiofiles` - Async file operations

## 🤖 Bot Capabilities

The bot can identify music from:
- Live recordings
- Phone speakers
- Bluetooth/audio system playback
- Short audio clips (10+ seconds recommended)
- Background music in videos

## 🔧 Advanced Configuration

### Audio Recognition Optimization
- Minimum 10-15 seconds of clear audio
- Avoid heavy background noise
- Music should be the primary audio source

### API Rate Limits
- ShazamIO: No strict limits for basic usage
- Last.fm: 5 requests per second per IP
- Spotify: Standard rate limits apply

### Performance Tips
- Bot handles multiple concurrent users
- Audio files are processed asynchronously
- Temporary files auto-deleted after processing

## 📞 Support

For issues, feature requests, or questions:
1. Check the logs for error details
2. Verify API keys are correctly configured
3. Ensure audio quality is sufficient for recognition

## 🎵 Enjoy discovering music with your new Telegram Music Bot! 🎵