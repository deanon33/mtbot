import os
import json
import logging
import tempfile
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class DirectShazamMusicBot:
    def __init__(self):
        # Base URLs for current Shazam.com API
        self.base_url = "https://www.shazam.com"
        self.api_base = "https://www.shazam.com/discovery/v5"
        self.charts_base = "https://www.shazam.com/shazam/v3"
        
        # Session for HTTP requests
        self.session = None

    async def get_session(self):
        """Get or create aiohttp session"""
        if self.session is None:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.shazam.com/',
            }
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request to Shazam API"""
        try:
            session = await self.get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {response.status} - {url}")
                    return None
        except Exception as e:
            logger.error(f"Request error: {e}")
            return None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command handler"""
        welcome_message = """
🎵 **Welcome to the Direct Shazam API Music Bot!** 🎵

🚀 **Using REAL Shazam.com endpoints - Always up to date!**

Here's what I can do for you:

🔎🎵 **Music Search** - /search\\_track bohemian rhapsody
🔎👨‍🎤 **Artist Search** - /search\\_artist taylor swift
📊 **Charts Commands:**
• /charts\\_global - Global Top 200 charts
• /charts\\_country US - Country charts (US, UK, etc.)
• /charts\\_city "New York" US - City charts
• /charts\\_discovery - Discovery charts (trending)
• /charts\\_genre rock - Genre charts

**🎧 Note:** Audio recognition requires ShazamIO library (currently has endpoint issues)

✨ *Using current Shazam.com API endpoints for maximum compatibility!*
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

    async def search_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for tracks using direct Shazam API"""
        if not context.args:
            await update.message.reply_text("Please provide a search query! Usage: /search\\_track bohemian rhapsody")
            return

        query = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching Shazam for tracks matching '{query}'...")

        try:
            # Use current Shazam search endpoint
            search_url = f"{self.api_base}/en/US/web/-/search"
            params = {
                'query': query,
                'numResults': 5,
                'offset': 0,
                'types': 'songs'
            }
            
            result = await self.make_request(search_url, params)
            
            if not result or 'tracks' not in result or not result['tracks']['hits']:
                await update.message.reply_text(f"❌ No tracks found matching '{query}' on Shazam")
                return

            response = f"🔎🎶 **Track Search Results** (Direct Shazam API)\n\n"
            response += f"Search query: {query}\n\n"

            for i, hit in enumerate(result['tracks']['hits'][:5], 1):
                track = hit.get('track', {})
                title = track.get('title', 'Unknown')
                artist = track.get('subtitle', 'Unknown Artist')
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n"
                
                # Add Shazam URL if available
                if 'url' in track:
                    response += f"   🔗 [Listen on Shazam]({track['url']})\n"
                
                response += "\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Track search error: {e}")
            await update.message.reply_text("❌ An error occurred while searching for tracks.")

    async def search_artists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for artists using direct Shazam API"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /search\\_artist taylor swift")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching Shazam for artists matching '{artist_name}'...")

        try:
            # Use current Shazam search endpoint
            search_url = f"{self.api_base}/en/US/web/-/search"
            params = {
                'query': artist_name,
                'numResults': 5,
                'offset': 0,
                'types': 'artists'
            }
            
            result = await self.make_request(search_url, params)
            
            if not result or 'artists' not in result or not result['artists']['hits']:
                await update.message.reply_text(f"❌ No artists found matching '{artist_name}' on Shazam")
                return

            response = f"🔎👨‍🎤 **Artist Search Results** (Direct Shazam API)\n\n"
            response += f"Search query: {artist_name}\n\n"

            for i, hit in enumerate(result['artists']['hits'][:5], 1):
                artist = hit.get('artist', {})
                name = artist.get('name', 'Unknown')
                
                response += f"{i}\\. 👨‍🎤 **{name}**\n"
                
                if 'url' in artist:
                    response += f"   🔗 [View on Shazam]({artist['url']})\n"
                
                response += "\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Artist search error: {e}")
            await update.message.reply_text("❌ An error occurred while searching for artists.")

    async def get_global_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get global top charts using current Shazam API"""
        await update.message.reply_text("🔍 Getting global top tracks from Shazam...")

        try:
            # Use current Shazam charts endpoint
            charts_url = f"{self.charts_base}/en-US/GB/web/-/tracks/ip-global-chart-top-200"
            params = {
                'pageSize': 10,
                'startFrom': 0
            }
            
            result = await self.make_request(charts_url, params)
            
            if not result or 'tracks' not in result:
                # Try alternative endpoint
                charts_url = "https://www.shazam.com/charts/top-200/global"
                result = await self.make_request(charts_url)
            
            if not result:
                await update.message.reply_text("🌐 **Global charts temporarily unavailable**\n\n❗ Trying alternative methods...\n\n• Use `/charts_country US` for US charts\n• Use `/search_track [song]` for specific searches")
                return

            response = f"🔝🎶🌏 **Global Top Tracks** (Shazam)\n\n"

            # Handle different response formats
            tracks = result.get('tracks', [])
            if isinstance(tracks, dict) and 'hits' in tracks:
                tracks = tracks['hits']

            for i, track_data in enumerate(tracks[:5], 1):
                if isinstance(track_data, dict):
                    track = track_data.get('track', track_data)
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                else:
                    title = 'Unknown'
                    artist = 'Unknown Artist'
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Global charts error: {e}")
            await update.message.reply_text("❌ Global charts are temporarily unavailable. Please try country-specific charts.")

    async def get_country_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get country charts using current Shazam API"""
        if not context.args:
            await update.message.reply_text("Please provide a country code! Usage: /charts\\_country US")
            return

        country_code = context.args[0].upper()
        await update.message.reply_text(f"🔍 Getting top tracks for {country_code}...")

        try:
            # Use current Shazam charts endpoint structure
            charts_url = f"https://www.shazam.com/charts/top-200/{country_code.lower()}"
            
            result = await self.make_request(charts_url)
            
            if not result:
                # Try alternative API endpoint
                charts_url = f"{self.charts_base}/en-US/{country_code}/web/-/tracks/top-200"
                params = {'pageSize': 10, 'startFrom': 0}
                result = await self.make_request(charts_url, params)
            
            if not result:
                await update.message.reply_text(f"❌ No charts found for {country_code}")
                return

            response = f"🔝🎶🏳️‍🌈 **Top Tracks in {country_code}**\n\n"

            # Handle different response formats
            tracks = result.get('tracks', [])
            if isinstance(tracks, dict) and 'hits' in tracks:
                tracks = tracks['hits']

            for i, track_data in enumerate(tracks[:5], 1):
                if isinstance(track_data, dict):
                    track = track_data.get('track', track_data)
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                else:
                    title = 'Unknown'
                    artist = 'Unknown Artist'
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Country charts error: {e}")
            await update.message.reply_text(f"❌ An error occurred while fetching {country_code} charts.")

    async def get_city_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get city charts using current Shazam API"""
        if len(context.args) < 2:
            await update.message.reply_text("Please provide city and country! Usage: /charts\\_city \"New York\" US")
            return

        city_name = context.args[0].strip('"\'')
        country_code = context.args[1].upper()
        
        await update.message.reply_text(f"🔍 Getting top tracks in {city_name}, {country_code}...")

        try:
            # Use current Shazam city charts endpoint
            charts_url = f"https://www.shazam.com/charts/top-50/{country_code.lower()}/{city_name.lower().replace(' ', '-')}"
            
            result = await self.make_request(charts_url)
            
            if not result:
                await update.message.reply_text(f"❌ No charts found for {city_name}, {country_code}")
                return

            response = f"🔝🎶🏙️ **Top Tracks in {city_name}, {country_code}**\n\n"

            tracks = result.get('tracks', [])
            if isinstance(tracks, dict) and 'hits' in tracks:
                tracks = tracks['hits']

            for i, track_data in enumerate(tracks[:5], 1):
                if isinstance(track_data, dict):
                    track = track_data.get('track', track_data)
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                else:
                    title = 'Unknown'
                    artist = 'Unknown Artist'
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"City charts error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching city charts.")

    async def get_discovery_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get discovery/viral charts using current Shazam API"""
        await update.message.reply_text("🔍 Getting trending/discovery tracks from Shazam...")

        try:
            # Use current Shazam discovery endpoint
            charts_url = f"https://www.shazam.com/charts/discovery/global"
            
            result = await self.make_request(charts_url)
            
            if not result:
                # Try alternative endpoint
                charts_url = f"{self.charts_base}/en-US/GB/web/-/tracks/discovery-chart"
                params = {'pageSize': 10, 'startFrom': 0}
                result = await self.make_request(charts_url, params)
            
            if not result:
                await update.message.reply_text("❌ Discovery charts temporarily unavailable")
                return

            response = f"🔥 **Discovery/Trending Tracks** (Shazam)\n\n"

            tracks = result.get('tracks', [])
            if isinstance(tracks, dict) and 'hits' in tracks:
                tracks = tracks['hits']

            for i, track_data in enumerate(tracks[:5], 1):
                if isinstance(track_data, dict):
                    track = track_data.get('track', track_data)
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                else:
                    title = 'Unknown'
                    artist = 'Unknown Artist'
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Discovery charts error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching discovery charts.")

    async def get_genre_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get genre charts using current Shazam API"""
        if not context.args:
            await update.message.reply_text("Please provide a genre! Usage: /charts\\_genre rock\n\nAvailable: rock, pop, hip-hop, dance, electronic, country")
            return

        genre = ' '.join(context.args).lower().replace('_', '-').replace(' ', '-')
        await update.message.reply_text(f"🔍 Getting top {genre} tracks worldwide...")

        try:
            # Use current Shazam genre charts endpoint
            charts_url = f"https://www.shazam.com/charts/genre/global/{genre}"
            
            result = await self.make_request(charts_url)
            
            if not result:
                await update.message.reply_text(f"❌ No {genre} charts found. Available genres: rock, pop, hip-hop, dance, electronic, country")
                return

            response = f"🔝🎶🌏🎸 **Top {genre.title()} Tracks Worldwide**\n\n"

            tracks = result.get('tracks', [])
            if isinstance(tracks, dict) and 'hits' in tracks:
                tracks = tracks['hits']

            for i, track_data in enumerate(tracks[:5], 1):
                if isinstance(track_data, dict):
                    track = track_data.get('track', track_data)
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                else:
                    title = 'Unknown'
                    artist = 'Unknown Artist'
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n"
                response += f"   🎸 Genre: {genre.title()}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Genre charts error: {e}")
            await update.message.reply_text(f"❌ An error occurred while fetching {genre} charts.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Help command handler"""
        help_text = """
🎵 **Direct Shazam API Music Bot Commands** 🎵

**🔍 Search:**
• `/search_track <query>` - Search for tracks
• `/search_artist <name>` - Search for artists

**📊 Charts (Real Shazam.com endpoints):**
• `/charts_global` - Global top tracks
• `/charts_country <code>` - Country charts (US, UK, etc.)
• `/charts_city "<city>" <country>` - City charts
• `/charts_discovery` - Trending/discovery tracks
• `/charts_genre <genre>` - Genre-specific charts

**ℹ️ Other:**
• `/help` - Show this help message
• `/start` - Welcome message

**💡 Examples:**
• `/search_track bohemian rhapsody`
• `/charts_country US`
• `/charts_city "New York" US`
• `/charts_genre rock`

✨ **Using real Shazam.com API endpoints for maximum reliability!**
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()

    def run(self):
        """Run the bot"""
        # Get bot token from environment
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
            return

        # Create application
        application = Application.builder().token(bot_token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search_track", self.search_tracks))
        application.add_handler(CommandHandler("search_artist", self.search_artists))
        application.add_handler(CommandHandler("charts_global", self.get_global_charts))
        application.add_handler(CommandHandler("charts_country", self.get_country_charts))
        application.add_handler(CommandHandler("charts_city", self.get_city_charts))
        application.add_handler(CommandHandler("charts_discovery", self.get_discovery_charts))
        application.add_handler(CommandHandler("charts_genre", self.get_genre_charts))

        # Start the bot
        logger.info("Starting Direct Shazam API Music Bot...")
        
        try:
            application.run_polling(allowed_updates=Update.ALL_TYPES)
        finally:
            # Cleanup
            asyncio.run(self.cleanup())

if __name__ == "__main__":
    bot = DirectShazamMusicBot()
    bot.run()