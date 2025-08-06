import os
import logging
import tempfile
from typing import Dict, List, Optional, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from shazamio import Shazam, Serialize, GenreMusic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ShazamMusicBot:
    def __init__(self):
        # Initialize ShazamIO
        self.shazam = Shazam()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command handler"""
        welcome_message = """
🎵 **Welcome to the ShazamIO Music Bot!** 🎵

🚀 **Powered entirely by ShazamIO - No additional APIs needed!**

Here's what I can do for you:

🔎🎵 **Recognize track** - Send me an audio file and I'll identify the song
👨‍🎤 **About artist** - /artist Taylor Swift
🎵📄 **About track** - /track 552406075 (use track ID)
🔎👨‍🎤 **Search artists** - /search\\_artist Lil
🔎🎶 **Search tracks** - /search\\_track bohemian rhapsody
🔝🎶🏙️ **Top tracks in city** - /top\\_city RU Moscow
🔝🎶🏳️‍🌈 **Top tracks in country** - /top\\_country NL
🔝🎶🌏🎸 **Top tracks by genre** - /top\\_genre rock
🔝🎶🌏 **Top tracks worldwide** - /top\\_world
🎵⌛ **Track listening count** - /listens 559284007
🎶💬 **Similar songs** - /similar 546891609

**🎧 Send me an audio file to start recognizing music!**

✨ *All powered by ShazamIO's amazing database!*
        """
        await update.message.reply_text(welcome_message, parse_mode=ParseMode.MARKDOWN)

    async def recognize_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Recognize track from audio file using ShazamIO"""
        try:
            if not update.message.audio and not update.message.voice and not update.message.video_note:
                await update.message.reply_text("Please send an audio file for music recognition! 🎵")
                return

            await update.message.reply_text("🔍 Analyzing your audio with Shazam... This may take a moment!")

            # Get the file
            if update.message.audio:
                file = await context.bot.get_file(update.message.audio.file_id)
            elif update.message.voice:
                file = await context.bot.get_file(update.message.voice.file_id)
            else:
                file = await context.bot.get_file(update.message.video_note.file_id)

            # Download the file
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, f"audio_{update.message.message_id}.ogg")
            await file.download_to_drive(file_path)

            # Recognize using Shazam - CORRECT METHOD
            try:
                result = await self.shazam.recognize(file_path)
                
                if not result or 'track' not in result:
                    await update.message.reply_text("❌ Sorry, I couldn't recognize this track. Try with a clearer audio sample!")
                    return

                track_info = result['track']
                
                # Use Serialize for clean data extraction
                try:
                    serialized = Serialize.track(result)
                    
                    response = f"🎵 **Track Recognized by Shazam!**\n\n"
                    response += f"🎼 **Title:** {serialized.title or 'Unknown'}\n"
                    response += f"👨‍🎤 **Artist:** {serialized.subtitle or 'Unknown Artist'}\n"
                    
                    if serialized.sections:
                        for section in serialized.sections:
                            if hasattr(section, 'metadata') and section.metadata:
                                for meta in section.metadata:
                                    if meta.title == 'Album':
                                        response += f"💿 **Album:** {meta.text}\n"
                                    elif meta.title == 'Released':
                                        response += f"📅 **Released:** {meta.text}\n"
                                    elif meta.title == 'Genre':
                                        response += f"🎸 **Genre:** {meta.text}\n"

                    if hasattr(serialized, 'shazam_count') and serialized.shazam_count:
                        response += f"📊 **Shazam Count:** {serialized.shazam_count:,} recognitions\n"

                    # Add streaming links
                    if serialized.apple_music_url:
                        response += f"\n🎧 **Listen on:**\n• Apple Music\n"
                    if serialized.spotify_url:
                        response += f"• Spotify\n"

                    # Add action buttons with track key
                    track_key = track_info.get('key', '')
                    keyboard = [
                        [InlineKeyboardButton("🎶 Similar Songs", callback_data=f"similar_{track_key}")],
                        [InlineKeyboardButton("📊 Listening Count", callback_data=f"listens_{track_key}")],
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    
                    await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
                    
                except Exception as serialize_error:
                    logger.error(f"Serialization error: {serialize_error}")
                    # Fallback to raw data
                    title = track_info.get('title', 'Unknown')
                    artist = track_info.get('subtitle', 'Unknown Artist')
                    
                    response = f"🎵 **Track Recognized by Shazam!**\n\n"
                    response += f"🎼 **Title:** {title}\n"
                    response += f"👨‍🎤 **Artist:** {artist}\n"
                    
                    await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

            except Exception as e:
                logger.error(f"Shazam recognition error: {e}")
                await update.message.reply_text("❌ Error during recognition. Please try again with a different audio file.")
                
            finally:
                # Clean up the file
                if os.path.exists(file_path):
                    os.remove(file_path)

        except Exception as e:
            logger.error(f"Audio recognition error: {e}")
            await update.message.reply_text("❌ An error occurred while processing your audio. Please try again!")

    async def search_artists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for artists using ShazamIO"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /search\\_artist Lil")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching Shazam for artists matching '{artist_name}'...")

        try:
            # CORRECT METHOD - search_artist with query parameter
            artists = await self.shazam.search_artist(query=artist_name, limit=5)
            
            if not artists or 'artists' not in artists or not artists['artists']['hits']:
                await update.message.reply_text(f"❌ No artists found matching '{artist_name}' in Shazam")
                return

            response = f"🔎👨‍🎤 **Artist Search Results** (Shazam)\n\n"
            response += f"Search query: {artist_name}\n\n"

            for i, hit in enumerate(artists['artists']['hits'][:5], 1):
                try:
                    # Use Serialize for clean data
                    serialized = Serialize.artist(data=hit)
                    response += f"{i}\\. 👨‍🎤 **{serialized.name or 'Unknown'}**\n"
                    if hasattr(serialized, 'adamid') and serialized.adamid:
                        response += f"   🆔 Shazam ID: {serialized.adamid}\n"
                    response += "\n"
                except:
                    # Fallback to raw data
                    artist_data = hit.get('artist', {})
                    name = artist_data.get('name', 'Unknown')
                    response += f"{i}\\. 👨‍🎤 **{name}**\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Artist search error: {e}")
            await update.message.reply_text("❌ An error occurred while searching for artists in Shazam.")

    async def search_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for tracks using ShazamIO"""
        if not context.args:
            await update.message.reply_text("Please provide a search query! Usage: /search\\_track bohemian rhapsody")
            return

        query = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching Shazam for tracks matching '{query}'...")

        try:
            # CORRECT METHOD - search_track with query parameter
            tracks = await self.shazam.search_track(query=query, limit=5)
            
            if not tracks or 'tracks' not in tracks or not tracks['tracks']['hits']:
                await update.message.reply_text(f"❌ No tracks found matching '{query}' in Shazam")
                return

            response = f"🔎🎶 **Track Search Results** (Shazam)\n\n"
            response += f"Search query: {query}\n\n"

            for i, hit in enumerate(tracks['tracks']['hits'][:5], 1):
                track_data = hit['track']
                title = track_data.get('title', 'Unknown')
                artist = track_data.get('subtitle', 'Unknown Artist')
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n"
                
                # Add track key for further actions
                track_key = track_data.get('key', '')
                if track_key:
                    response += f"   🔑 Track ID: {track_key}\n"
                
                response += "\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Track search error: {e}")
            await update.message.reply_text("❌ An error occurred while searching for tracks in Shazam.")

    async def get_track_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get track information by track ID"""
        if not context.args:
            await update.message.reply_text("Please provide a track ID! Usage: /track 552406075")
            return

        try:
            track_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid track ID number!")
            return

        await update.message.reply_text(f"🔍 Getting information for track ID {track_id}...")

        try:
            # CORRECT METHOD - track_about
            about_track = await self.shazam.track_about(track_id=track_id)
            
            if not about_track:
                await update.message.reply_text(f"❌ No information found for track ID {track_id}")
                return

            # Use Serialize for clean data
            try:
                serialized = Serialize.track(data=about_track)
                
                response = f"🎵 **Track Information** (via Shazam)\n\n"
                response += f"🎼 **Title:** {serialized.title or 'Unknown'}\n"
                response += f"👨‍🎤 **Artist:** {serialized.subtitle or 'Unknown'}\n"
                
                if hasattr(serialized, 'apple_music_url') and serialized.apple_music_url:
                    response += f"🎧 **Apple Music:** Available\n"
                if hasattr(serialized, 'spotify_url') and serialized.spotify_url:
                    response += f"🎧 **Spotify:** Available\n"
                
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                
            except Exception as serialize_error:
                logger.error(f"Serialization error: {serialize_error}")
                await update.message.reply_text(f"✅ Found track ID {track_id} but couldn't parse details properly.")

        except Exception as e:
            logger.error(f"Track about error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching track information.")

    async def get_listening_counter(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get listening count for a track"""
        if not context.args:
            await update.message.reply_text("Please provide a track ID! Usage: /listens 559284007")
            return

        try:
            track_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid track ID number!")
            return

        await update.message.reply_text(f"🔍 Getting listening count for track ID {track_id}...")

        try:
            # CORRECT METHOD - listening_counter
            count = await self.shazam.listening_counter(track_id=track_id)
            
            response = f"🎵⌛ **Listening Statistics**\n\n"
            response += f"🔢 **Track ID:** {track_id}\n"
            response += f"▶️ **Total Plays:** {count:,}\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Listening counter error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching listening statistics.")

    async def get_related_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get similar/related tracks"""
        if not context.args:
            await update.message.reply_text("Please provide a track ID! Usage: /similar 546891609")
            return

        try:
            track_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Please provide a valid track ID number!")
            return

        await update.message.reply_text(f"🔍 Finding songs similar to track ID {track_id}...")

        try:
            # CORRECT METHOD - related_tracks
            related = await self.shazam.related_tracks(track_id=track_id, limit=5)
            
            if not related or 'tracks' not in related:
                await update.message.reply_text(f"❌ No related tracks found for track ID {track_id}")
                return

            response = f"🎶💬 **Similar Songs** (via Shazam)\n\n"
            response += f"Based on track ID: {track_id}\n\n"

            for i, track in enumerate(related['tracks'][:5], 1):
                try:
                    serialized = Serialize.track(data={'track': track})
                    title = serialized.title or 'Unknown'
                    artist = serialized.subtitle or 'Unknown Artist'
                except:
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Related tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while finding similar songs.")

    async def get_top_city_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks in a city"""
        if len(context.args) < 2:
            await update.message.reply_text("Please provide country and city! Usage: /top\\_city RU Moscow")
            return

        country_code = context.args[0].upper()
        city_name = ' '.join(context.args[1:])
        
        await update.message.reply_text(f"🔍 Getting top tracks in {city_name}, {country_code}...")

        try:
            # CORRECT METHOD - top_city_tracks
            top_tracks = await self.shazam.top_city_tracks(country_code=country_code, city_name=city_name, limit=10)
            
            if not top_tracks or 'tracks' not in top_tracks:
                await update.message.reply_text(f"❌ No charts found for {city_name}, {country_code}")
                return

            response = f"🔝🎶🏙️ **Top Tracks in {city_name}, {country_code}**\n\n"

            for i, track in enumerate(top_tracks['tracks'][:5], 1):
                try:
                    serialized = Serialize.track(data={'track': track})
                    title = serialized.title or 'Unknown'
                    artist = serialized.subtitle or 'Unknown Artist'
                except:
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top city tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching city charts.")

    async def get_top_country_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks in a country"""
        if not context.args:
            await update.message.reply_text("Please provide a country code! Usage: /top\\_country NL")
            return

        country_code = context.args[0].upper()
        limit = 5
        
        await update.message.reply_text(f"🔍 Getting top tracks in {country_code}...")

        try:
            # CORRECT METHOD - top_country_tracks
            top_tracks = await self.shazam.top_country_tracks(country_code, limit)
            
            if not top_tracks or 'tracks' not in top_tracks:
                await update.message.reply_text(f"❌ No charts found for country {country_code}")
                return

            response = f"🔝🎶🏳️‍🌈 **Top Tracks in {country_code}**\n\n"

            for i, track in enumerate(top_tracks['tracks'][:5], 1):
                try:
                    serialized = Serialize.track(data={'track': track})
                    title = serialized.title or 'Unknown'
                    artist = serialized.subtitle or 'Unknown Artist'
                except:
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top country tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching country charts.")

    async def get_top_world_genre_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks by genre worldwide"""
        if not context.args:
            await update.message.reply_text("Please provide a genre! Usage: /top\\_genre rock\n\nAvailable: ROCK, POP, HIP\\_HOP\\_RAP, DANCE, ELECTRONIC, ALTERNATIVE, COUNTRY")
            return

        genre_name = ' '.join(context.args).upper().replace(' ', '_').replace('-', '_')
        
        # Map to GenreMusic enum (based on ShazamIO documentation)
        genre_mapping = {
            'ROCK': GenreMusic.ROCK,
            'POP': GenreMusic.POP,
            'HIP_HOP_RAP': GenreMusic.HIP_HOP_RAP,
            'HIP_HOP': GenreMusic.HIP_HOP_RAP,
            'RAP': GenreMusic.HIP_HOP_RAP,
            'DANCE': GenreMusic.DANCE,
            'ELECTRONIC': GenreMusic.ELECTRONIC,
            'ALTERNATIVE': GenreMusic.ALTERNATIVE,
            'COUNTRY': GenreMusic.COUNTRY,
        }

        if genre_name not in genre_mapping:
            await update.message.reply_text(f"❌ Genre '{genre_name}' not supported.\n\nAvailable: {', '.join(genre_mapping.keys())}")
            return

        genre_enum = genre_mapping[genre_name]
        await update.message.reply_text(f"🔍 Getting top {genre_name.lower()} tracks worldwide...")

        try:
            # CORRECT METHOD - top_world_genre_tracks  
            top_tracks = await self.shazam.top_world_genre_tracks(genre=genre_enum, limit=10)
            
            if not top_tracks or 'tracks' not in top_tracks:
                await update.message.reply_text(f"❌ No {genre_name.lower()} tracks found in global charts")
                return

            response = f"🔝🎶🌏🎸 **Top {genre_name.title()} Tracks Worldwide**\n\n"

            for i, track in enumerate(top_tracks['tracks'][:5], 1):
                try:
                    serialized = Serialize.track(data={'track': track})
                    title = serialized.title or 'Unknown'
                    artist = serialized.subtitle or 'Unknown Artist'
                except:
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n"
                response += f"   🎸 Genre: {genre_name.title()}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top world genre tracks error: {e}")
            await update.message.reply_text(f"❌ An error occurred while fetching {genre_name.lower()} charts.")

    async def get_top_world_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks worldwide"""
        await update.message.reply_text("🔍 Getting worldwide top tracks from Shazam...")

        try:
            # CORRECT METHOD - top_world_tracks
            top_tracks = await self.shazam.top_world_tracks(limit=10)
            
            if not top_tracks or 'tracks' not in top_tracks:
                await update.message.reply_text("❌ Unable to fetch global charts from Shazam.")
                return

            response = f"🔝🎶🌏 **Top Tracks Worldwide** (Shazam)\n\n"

            for i, track in enumerate(top_tracks['tracks'][:5], 1):
                try:
                    serialized = Serialize.track(data={'track': track})
                    title = serialized.title or 'Unknown'
                    artist = serialized.subtitle or 'Unknown Artist'
                except:
                    title = track.get('title', 'Unknown')
                    artist = track.get('subtitle', 'Unknown Artist')
                
                response += f"{i}\\. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top world tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching global charts from Shazam.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data
        
        try:
            if data.startswith("similar_"):
                track_key = data[8:]
                if track_key.isdigit():
                    context.args = [track_key]
                    await self.get_related_tracks(update, context)
                else:
                    await query.edit_message_text("❌ Invalid track ID for similar songs.")
                
            elif data.startswith("listens_"):
                track_key = data[8:]
                if track_key.isdigit():
                    context.args = [track_key]
                    await self.get_listening_counter(update, context)
                else:
                    await query.edit_message_text("❌ Invalid track ID for listening count.")
                
        except Exception as e:
            logger.error(f"Button callback error: {e}")
            await query.edit_message_text("❌ An error occurred while processing your request.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Help command handler"""
        help_text = """
🎵 **ShazamIO Music Bot Commands** 🎵

**🔎 Recognition & Info:**
• Send audio file - Recognize track automatically
• `/track <track_id>` - Get track details by ID
• `/listens <track_id>` - Get listening statistics

**🔍 Search:**
• `/search_artist <name>` - Search for artists
• `/search_track <query>` - Search for tracks
• `/similar <track_id>` - Find similar songs

**📊 Charts (Shazam Data):**
• `/top_world` - Global top tracks
• `/top_genre <genre>` - Top tracks by genre
• `/top_country <code>` - Top tracks by country (NL, US, etc.)
• `/top_city <country> <city>` - Top tracks in city

**ℹ️ Other:**
• `/help` - Show this help message
• `/start` - Welcome message

**💡 Tips:**
- Send audio files for instant Shazam recognition!
- Use track IDs from search results for detailed info
- Available genres: rock, pop, hip-hop, electronic, etc.

✨ **All powered by ShazamIO - No additional APIs needed!**
        """
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    def run(self):
        """Run the bot"""
        # Get bot token from environment
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
            return

        # Create application
        application = Application.builder().token(bot_token).build()

        # Add handlers - CORRECT COMMAND NAMES
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search_artist", self.search_artists))
        application.add_handler(CommandHandler("search_track", self.search_tracks))
        application.add_handler(CommandHandler("track", self.get_track_about))
        application.add_handler(CommandHandler("listens", self.get_listening_counter))
        application.add_handler(CommandHandler("similar", self.get_related_tracks))
        application.add_handler(CommandHandler("top_city", self.get_top_city_tracks))
        application.add_handler(CommandHandler("top_country", self.get_top_country_tracks))
        application.add_handler(CommandHandler("top_genre", self.get_top_world_genre_tracks))
        application.add_handler(CommandHandler("top_world", self.get_top_world_tracks))
        
        # Add audio message handler for music recognition
        application.add_handler(MessageHandler(
            filters.AUDIO | filters.VOICE | filters.VIDEO_NOTE, 
            self.recognize_audio
        ))
        
        # Add callback query handler for buttons
        application.add_handler(CallbackQueryHandler(self.button_callback))

        # Start the bot
        logger.info("Starting ShazamIO Music Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = ShazamMusicBot()
    bot.run()