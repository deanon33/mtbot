import os
import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from shazamio import Shazam, GenreMusic
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
👨‍🎤 **About artist** - /artist \\<artist\\_name\\>
🎵📄 **About track** - /track \\<artist\\> - \\<song\\>
🔎👨‍🎤 **Search artists** - /search\\_artist \\<name\\>
🔎🎶 **Search tracks** - /search\\_track \\<query\\>
🔝🎶👨‍🎤 **Top artist tracks** - /top\\_artist \\<artist\\_name\\>
🔝🎶🌏 **Top tracks worldwide** - /top\\_world
🔝🎶🌏🎸 **Top tracks by genre** - /top\\_genre \\<genre\\>
🎶💬 **Similar songs** - /similar \\<artist\\> - \\<song\\>
🎵📊 **Track charts** - /charts

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
            file_path = f"/tmp/audio_{update.message.message_id}.ogg"
            await file.download_to_drive(file_path)

            # Recognize using Shazam
            try:
                result = await self.shazam.recognize_song(file_path)
                
                if not result or 'track' not in result:
                    await update.message.reply_text("❌ Sorry, I couldn't recognize this track. Try with a clearer audio sample!")
                    return

                track_info = result['track']
                
                # Format the response with rich information
                title = track_info.get('title', 'Unknown')
                artist = track_info.get('subtitle', 'Unknown Artist')
                
                response = f"🎵 **Track Recognized by Shazam!**\n\n"
                response += f"🎼 **Title:** {title}\n"
                response += f"👨‍🎤 **Artist:** {artist}\n"
                
                # Extract detailed metadata from Shazam
                if 'sections' in track_info:
                    for section in track_info['sections']:
                        if section.get('type') == 'SONG':
                            metadata = section.get('metadata', [])
                            for meta in metadata:
                                if meta.get('title') == 'Album':
                                    response += f"💿 **Album:** {meta.get('text', 'Unknown')}\n"
                                elif meta.get('title') == 'Released':
                                    response += f"📅 **Released:** {meta.get('text', 'Unknown')}\n"
                                elif meta.get('title') == 'Label':
                                    response += f"🏷️ **Label:** {meta.get('text', 'Unknown')}\n"
                                elif meta.get('title') == 'Genre':
                                    response += f"🎸 **Genre:** {meta.get('text', 'Unknown')}\n"

                # Add Shazam count if available
                if 'shazam_count' in track_info:
                    count = track_info['shazam_count']
                    response += f"📊 **Shazam Count:** {count:,} recognitions\n"

                # Add streaming links if available
                if 'hub' in track_info and 'actions' in track_info['hub']:
                    actions = track_info['hub']['actions']
                    if actions:
                        response += f"\n🎧 **Listen on:**\n"
                        for action in actions[:3]:  # Show first 3 platforms
                            if 'name' in action:
                                response += f"• {action['name']}\n"

                # Add action buttons
                keyboard = [
                    [InlineKeyboardButton("👨‍🎤 About Artist", callback_data=f"artist_{artist}")],
                    [InlineKeyboardButton("🎵 About Track", callback_data=f"track_{artist}_{title}")],
                    [InlineKeyboardButton("🎶 Similar Songs", callback_data=f"similar_{artist}_{title}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

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

    async def get_artist_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get information about an artist using ShazamIO"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /artist <artist_name>")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching Shazam for information about {artist_name}...")

        try:
            # Get artist info from Shazam
            artists = await self.shazam.search_artist(artist_name)
            
            if not artists or 'artists' not in artists or not artists['artists']['hits']:
                await update.message.reply_text(f"❌ Sorry, I couldn't find information about '{artist_name}' in Shazam's database")
                return

            artist_data = artists['artists']['hits'][0]['artist']
            
            response = f"👨‍🎤 **Artist Information** (via Shazam)\n\n"
            response += f"🎵 **Name:** {artist_data.get('name', 'Unknown')}\n"
            
            if 'adamid' in artist_data:
                response += f"🆔 **Shazam ID:** {artist_data['adamid']}\n"

            # Try to get more detailed artist info
            try:
                if 'adamid' in artist_data:
                    artist_details = await self.shazam.artist_about(artist_data['adamid'])
                    if artist_details and 'data' in artist_details:
                        data = artist_details['data'][0] if artist_details['data'] else {}
                        if 'attributes' in data:
                            attrs = data['attributes']
                            if 'genreNames' in attrs:
                                genres = ', '.join(attrs['genreNames'])
                                response += f"🎸 **Genres:** {genres}\n"
                            if 'origin' in attrs:
                                response += f"🌍 **Origin:** {attrs['origin']}\n"
            except Exception as e:
                logger.error(f"Detailed artist info error: {e}")

            # Add action buttons
            keyboard = [
                [InlineKeyboardButton("🔝 Top Tracks", callback_data=f"top_artist_{artist_name}")],
                [InlineKeyboardButton("🎶 Similar Artists", callback_data=f"similar_artist_{artist_name}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Artist info error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching artist information from Shazam.")

    async def get_track_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get information about a track using ShazamIO"""
        if len(context.args) < 3 or '-' not in ' '.join(context.args):
            await update.message.reply_text("Please provide artist and track! Usage: /track <artist> - <song>")
            return

        query = ' '.join(context.args)
        try:
            artist, track = query.split(' - ', 1)
            artist = artist.strip()
            track = track.strip()
        except ValueError:
            await update.message.reply_text("Please use the format: /track <artist> - <song>")
            return

        await update.message.reply_text(f"🔍 Searching Shazam for '{track}' by {artist}...")

        try:
            # Search for the track using Shazam
            search_results = await self.shazam.search_track(f"{artist} {track}")
            
            if not search_results or 'tracks' not in search_results or not search_results['tracks']['hits']:
                await update.message.reply_text(f"❌ Sorry, I couldn't find '{track}' by {artist} in Shazam's database")
                return

            track_data = search_results['tracks']['hits'][0]['track']
            
            response = f"🎵 **Track Information** (via Shazam)\n\n"
            response += f"🎼 **Title:** {track_data.get('title', track)}\n"
            response += f"👨‍🎤 **Artist:** {track_data.get('subtitle', artist)}\n"
            
            # Extract rich metadata from Shazam
            if 'sections' in track_data:
                for section in track_data['sections']:
                    if section.get('type') == 'SONG':
                        metadata = section.get('metadata', [])
                        for meta in metadata:
                            if meta.get('title') == 'Album':
                                response += f"💿 **Album:** {meta.get('text', 'Unknown')}\n"
                            elif meta.get('title') == 'Released':
                                response += f"📅 **Released:** {meta.get('text', 'Unknown')}\n"
                            elif meta.get('title') == 'Genre':
                                response += f"🎸 **Genre:** {meta.get('text', 'Unknown')}\n"
                            elif meta.get('title') == 'Label':
                                response += f"🏷️ **Label:** {meta.get('text', 'Unknown')}\n"

            # Add Shazam recognition count
            if 'shazam_count' in track_data:
                count = track_data['shazam_count']
                response += f"📊 **Shazam Recognitions:** {count:,}\n"

            # Add streaming services if available
            if 'hub' in track_data and 'actions' in track_data['hub']:
                actions = track_data['hub']['actions']
                if actions:
                    response += f"\n🎧 **Available on:**\n"
                    for action in actions[:3]:
                        if 'name' in action:
                            response += f"• {action['name']}\n"

            # Add action buttons
            keyboard = [
                [InlineKeyboardButton("🎶 Similar Songs", callback_data=f"similar_{artist}_{track}")],
                [InlineKeyboardButton("👨‍🎤 About Artist", callback_data=f"artist_{artist}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Track info error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching track information from Shazam.")

    async def search_artists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for artists using ShazamIO"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /search_artist <name>")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching Shazam for artists matching '{artist_name}'...")

        try:
            # Search using Shazam
            artists = await self.shazam.search_artist(artist_name)
            
            if not artists or 'artists' not in artists or not artists['artists']['hits']:
                await update.message.reply_text(f"❌ No artists found matching '{artist_name}' in Shazam")
                return

            response = f"🔎👨‍🎤 **Artist Search Results** (Shazam)\n\n"
            response += f"Search query: {artist_name}\n\n"

            for i, hit in enumerate(artists['artists']['hits'][:5], 1):
                artist_data = hit['artist']
                name = artist_data.get('name', 'Unknown')
                response += f"{i}. 👨‍🎤 **{name}**\n"
                
                if 'adamid' in artist_data:
                    response += f"   🆔 Shazam ID: {artist_data['adamid']}\n"
                response += "\n"

            # Add action buttons for the first result
            if artists['artists']['hits']:
                first_artist = artists['artists']['hits'][0]['artist']['name']
                keyboard = [
                    [InlineKeyboardButton("ℹ️ About This Artist", callback_data=f"artist_{first_artist}")],
                    [InlineKeyboardButton("🔝 Top Tracks", callback_data=f"top_artist_{first_artist}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Artist search error: {e}")
            await update.message.reply_text("❌ An error occurred while searching for artists in Shazam.")

    async def search_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for tracks using ShazamIO"""
        if not context.args:
            await update.message.reply_text("Please provide a search query! Usage: /search_track <query>")
            return

        query = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching Shazam for tracks matching '{query}'...")

        try:
            # Search using Shazam
            tracks = await self.shazam.search_track(query)
            
            if not tracks or 'tracks' not in tracks or not tracks['tracks']['hits']:
                await update.message.reply_text(f"❌ No tracks found matching '{query}' in Shazam")
                return

            response = f"🔎🎶 **Track Search Results** (Shazam)\n\n"
            response += f"Search query: {query}\n\n"

            for i, hit in enumerate(tracks['tracks']['hits'][:5], 1):
                track_data = hit['track']
                title = track_data.get('title', 'Unknown')
                artist = track_data.get('subtitle', 'Unknown Artist')
                
                response += f"{i}. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n"
                
                # Add Shazam count if available
                if 'shazam_count' in track_data:
                    count = track_data['shazam_count']
                    response += f"   📊 Shazams: {count:,}\n"
                
                # Add album info if available
                if 'sections' in track_data:
                    for section in track_data['sections']:
                        if section.get('type') == 'SONG':
                            metadata = section.get('metadata', [])
                            for meta in metadata:
                                if meta.get('title') == 'Album':
                                    response += f"   💿 Album: {meta.get('text', 'Unknown')}\n"
                                    break
                response += "\n"

            # Add action buttons for the first result
            if tracks['tracks']['hits']:
                first_track = tracks['tracks']['hits'][0]['track']
                first_title = first_track.get('title', 'Unknown')
                first_artist = first_track.get('subtitle', 'Unknown Artist')
                
                keyboard = [
                    [InlineKeyboardButton("ℹ️ About This Track", callback_data=f"track_{first_artist}_{first_title}")],
                    [InlineKeyboardButton("🎶 Similar Songs", callback_data=f"similar_{first_artist}_{first_title}")],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)
            else:
                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Track search error: {e}")
            await update.message.reply_text("❌ An error occurred while searching for tracks in Shazam.")

    async def get_top_artist_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks for an artist using ShazamIO"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /top_artist <artist_name>")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Getting top tracks for {artist_name} from Shazam...")

        try:
            # First, find the artist
            artists = await self.shazam.search_artist(artist_name)
            
            if not artists or 'artists' not in artists or not artists['artists']['hits']:
                await update.message.reply_text(f"❌ Artist '{artist_name}' not found in Shazam")
                return

            artist_data = artists['artists']['hits'][0]['artist']
            artist_id = artist_data.get('adamid')
            
            if not artist_id:
                await update.message.reply_text(f"❌ Cannot get top tracks for '{artist_name}' - missing artist ID")
                return

            # Get top tracks for the artist
            try:
                top_tracks = await self.shazam.artist_top_tracks(artist_id)
                
                response = f"🔝🎶👨‍🎤 **Top Tracks** (Shazam)\n\n"
                response += f"Artist: {artist_data.get('name', artist_name)}\n\n"

                if top_tracks and 'data' in top_tracks:
                    tracks_data = top_tracks['data']
                    
                    if tracks_data:
                        for i, track_info in enumerate(tracks_data[:5], 1):
                            if 'attributes' in track_info:
                                attrs = track_info['attributes']
                                title = attrs.get('name', 'Unknown')
                                album = attrs.get('albumName', 'Unknown Album')
                                
                                response += f"{i}. 🎵 **{title}**\n"
                                response += f"   💿 Album: {album}\n"
                                
                                if 'releaseDate' in attrs:
                                    response += f"   📅 Released: {attrs['releaseDate']}\n"
                                if 'durationInMillis' in attrs:
                                    duration_ms = attrs['durationInMillis']
                                    minutes = duration_ms // 60000
                                    seconds = (duration_ms % 60000) // 1000
                                    response += f"   ⏱️ Duration: {minutes}:{seconds:02d}\n"
                                response += "\n"
                    else:
                        response += "❌ No top tracks found for this artist in Shazam."
                else:
                    response += "❌ Unable to fetch top tracks from Shazam."

                await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
                
            except Exception as e:
                logger.error(f"Shazam top tracks error: {e}")
                await update.message.reply_text("❌ Unable to fetch top tracks from Shazam for this artist.")

        except Exception as e:
            logger.error(f"Top artist tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching top tracks.")

    async def get_top_world_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks worldwide using ShazamIO"""
        await update.message.reply_text("🔍 Getting worldwide top tracks from Shazam...")

        try:
            # Get global charts from Shazam
            charts = await self.shazam.top_world_tracks()
            
            response = f"🔝🎶🌏 **Top Tracks Worldwide** (Shazam)\n\n"

            if charts and 'data' in charts:
                tracks_data = charts['data']
                
                if tracks_data:
                    for i, track_info in enumerate(tracks_data[:10], 1):
                        if 'attributes' in track_info:
                            attrs = track_info['attributes']
                            title = attrs.get('name', 'Unknown')
                            artist = attrs.get('artistName', 'Unknown Artist')
                            
                            response += f"{i}. 🎵 **{title}**\n"
                            response += f"   👨‍🎤 by {artist}\n"
                            
                            if 'albumName' in attrs:
                                response += f"   💿 Album: {attrs['albumName']}\n"
                            response += "\n"
                else:
                    response += "❌ No chart data available from Shazam at this time."
            else:
                response += "❌ Unable to fetch global charts from Shazam."

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top world tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching global charts from Shazam.")

    async def get_top_genre_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks by genre using ShazamIO"""
        if not context.args:
            await update.message.reply_text("Please provide a genre! Usage: /top_genre <genre>\n\nAvailable genres: POP, ROCK, DANCE, HIP_HOP_RAP, ALTERNATIVE, INDIE_ROCK, COUNTRY, JAZZ, BLUES, FOLK, CLASSICAL, ELECTRONIC")
            return

        genre_name = ' '.join(context.args).upper().replace(' ', '_').replace('-', '_')
        
        # Map common genre names to ShazamIO GenreMusic enum
        genre_mapping = {
            'POP': GenreMusic.POP,
            'ROCK': GenreMusic.ROCK,
            'DANCE': GenreMusic.DANCE,
            'HIP_HOP': GenreMusic.HIP_HOP_RAP,
            'RAP': GenreMusic.HIP_HOP_RAP,
            'HIP_HOP_RAP': GenreMusic.HIP_HOP_RAP,
            'ALTERNATIVE': GenreMusic.ALTERNATIVE,
            'INDIE_ROCK': GenreMusic.INDIE_ROCK,
            'INDIE': GenreMusic.INDIE_ROCK,
            'COUNTRY': GenreMusic.COUNTRY,
            'JAZZ': GenreMusic.JAZZ,
            'BLUES': GenreMusic.BLUES,
            'FOLK': GenreMusic.FOLK,
            'CLASSICAL': GenreMusic.CLASSICAL,
            'ELECTRONIC': GenreMusic.ELECTRONIC,
        }

        if genre_name not in genre_mapping:
            await update.message.reply_text(f"❌ Genre '{genre_name}' not supported.\n\nAvailable genres: {', '.join(genre_mapping.keys())}")
            return

        genre_enum = genre_mapping[genre_name]
        await update.message.reply_text(f"🔍 Getting top {genre_name.lower()} tracks from Shazam...")

        try:
            # Get genre charts from Shazam
            charts = await self.shazam.top_world_genre_tracks(genre_enum, 10)
            
            response = f"🔝🎶🌏🎸 **Top {genre_name.title()} Tracks Worldwide** (Shazam)\n\n"

            if charts and 'data' in charts:
                tracks_data = charts['data']
                
                if tracks_data:
                    for i, track_info in enumerate(tracks_data[:5], 1):
                        if 'attributes' in track_info:
                            attrs = track_info['attributes']
                            title = attrs.get('name', 'Unknown')
                            artist = attrs.get('artistName', 'Unknown Artist')
                            
                            response += f"{i}. 🎵 **{title}**\n"
                            response += f"   👨‍🎤 by {artist}\n"
                            response += f"   🎸 Genre: {genre_name.title()}\n"
                            
                            if 'albumName' in attrs:
                                response += f"   💿 Album: {attrs['albumName']}\n"
                            response += "\n"
                else:
                    response += f"❌ No {genre_name.lower()} tracks found in Shazam charts."
            else:
                response += f"❌ Unable to fetch {genre_name.lower()} charts from Shazam."

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top genre tracks error: {e}")
            await update.message.reply_text(f"❌ An error occurred while fetching {genre_name.lower()} charts from Shazam.")

    async def get_similar_songs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get similar songs using ShazamIO's related tracks feature"""
        if len(context.args) < 3 or '-' not in ' '.join(context.args):
            await update.message.reply_text("Please provide artist and track! Usage: /similar <artist> - <song>")
            return

        query = ' '.join(context.args)
        try:
            artist, track = query.split(' - ', 1)
            artist = artist.strip()
            track = track.strip()
        except ValueError:
            await update.message.reply_text("Please use the format: /similar <artist> - <song>")
            return

        await update.message.reply_text(f"🔍 Finding songs similar to '{track}' by {artist} using Shazam...")

        try:
            # First find the track
            search_results = await self.shazam.search_track(f"{artist} {track}")
            
            if not search_results or 'tracks' not in search_results or not search_results['tracks']['hits']:
                await update.message.reply_text(f"❌ Could not find '{track}' by {artist} in Shazam to get similar songs")
                return

            track_data = search_results['tracks']['hits'][0]['track']
            track_id = track_data.get('key')
            
            if not track_id:
                await update.message.reply_text("❌ Unable to get track ID for similarity search")
                return

            response = f"🎶💬 **Similar Songs** (via Shazam)\n\n"
            response += f"Based on: {track} by {artist}\n\n"

            try:
                # Get related tracks from Shazam
                related = await self.shazam.related_tracks(track_id)
                
                if related and 'data' in related:
                    tracks_data = related['data']
                    
                    if tracks_data:
                        for i, track_info in enumerate(tracks_data[:5], 1):
                            if 'attributes' in track_info:
                                attrs = track_info['attributes']
                                title = attrs.get('name', 'Unknown')
                                artist_name = attrs.get('artistName', 'Unknown Artist')
                                
                                response += f"{i}. 🎵 **{title}**\n"
                                response += f"   👨‍🎤 by {artist_name}\n"
                                
                                if 'albumName' in attrs:
                                    response += f"   💿 Album: {attrs['albumName']}\n"
                                if 'genreNames' in attrs:
                                    genres = ', '.join(attrs['genreNames'])
                                    response += f"   🎸 Genre: {genres}\n"
                                response += "\n"
                    else:
                        response += "❌ No similar tracks found in Shazam's database."
                else:
                    response += "❌ Unable to fetch similar tracks from Shazam."
                    
            except Exception as e:
                logger.error(f"Shazam related tracks error: {e}")
                response += "❌ Error fetching similar tracks from Shazam."

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Similar songs error: {e}")
            await update.message.reply_text("❌ An error occurred while finding similar songs.")

    async def get_charts(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show available chart options"""
        response = """
📊 **Available Charts** (Shazam)

🌍 **Global Charts:**
• `/top_world` - Worldwide top tracks
• `/top_genre <genre>` - Top tracks by genre

🎸 **Available Genres:**
• POP, ROCK, DANCE, HIP_HOP, RAP
• ALTERNATIVE, INDIE, COUNTRY
• JAZZ, BLUES, FOLK, CLASSICAL, ELECTRONIC

👨‍🎤 **Artist Charts:**
• `/top_artist <artist_name>` - Top tracks by artist

🔍 **Examples:**
• `/top_genre rock`
• `/top_genre electronic`
• `/top_artist Taylor Swift`

✨ *All data powered by Shazam's global database!*
        """
        await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data
        
        try:
            if data.startswith("artist_"):
                artist_name = data[7:]
                await query.edit_message_text(f"🔍 Getting information about {artist_name} from Shazam...")
                
                # Get artist info
                try:
                    artists = await self.shazam.search_artist(artist_name)
                    
                    if not artists or 'artists' not in artists or not artists['artists']['hits']:
                        await query.edit_message_text(f"❌ Sorry, I couldn't find information about '{artist_name}' in Shazam")
                        return

                    artist_data = artists['artists']['hits'][0]['artist']
                    
                    response = f"👨‍🎤 **Artist Information** (via Shazam)\n\n"
                    response += f"🎵 **Name:** {artist_data.get('name', 'Unknown')}\n"
                    
                    if 'adamid' in artist_data:
                        response += f"🆔 **Shazam ID:** {artist_data['adamid']}\n"

                    await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
                    
                except Exception as e:
                    logger.error(f"Artist info error: {e}")
                    await query.edit_message_text("❌ An error occurred while fetching artist information from Shazam.")
                
            elif data.startswith("track_"):
                parts = data[6:].split("_", 1)
                if len(parts) == 2:
                    artist, track = parts
                    await query.edit_message_text(f"🔍 Getting information about '{track}' by {artist} from Shazam...")
                    
                    try:
                        search_results = await self.shazam.search_track(f"{artist} {track}")
                        
                        if not search_results or 'tracks' not in search_results or not search_results['tracks']['hits']:
                            await query.edit_message_text(f"❌ Sorry, I couldn't find '{track}' by {artist} in Shazam")
                            return

                        track_data = search_results['tracks']['hits'][0]['track']
                        
                        response = f"🎵 **Track Information** (via Shazam)\n\n"
                        response += f"🎼 **Title:** {track_data.get('title', track)}\n"
                        response += f"👨‍🎤 **Artist:** {track_data.get('subtitle', artist)}\n"
                        
                        # Extract metadata from Shazam
                        if 'sections' in track_data:
                            for section in track_data['sections']:
                                if section.get('type') == 'SONG':
                                    metadata = section.get('metadata', [])
                                    for meta in metadata:
                                        if meta.get('title') == 'Album':
                                            response += f"💿 **Album:** {meta.get('text', 'Unknown')}\n"
                                        elif meta.get('title') == 'Released':
                                            response += f"📅 **Released:** {meta.get('text', 'Unknown')}\n"

                        if 'shazam_count' in track_data:
                            count = track_data['shazam_count']
                            response += f"📊 **Shazam Recognitions:** {count:,}\n"

                        await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
                        
                    except Exception as e:
                        logger.error(f"Track info error: {e}")
                        await query.edit_message_text("❌ An error occurred while fetching track information from Shazam.")
                
        except Exception as e:
                          logger.error(f"Button callback error: {e}")
              await query.edit_message_text("❌ An error occurred while processing your request.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Help command handler"""
        help_text = """
🎵 **ShazamIO Music Bot Commands** 🎵

**🔎 Recognition & Info:**
• Send audio file - Recognize track automatically
• `/artist \\<name\\>` - Get artist information
• `/track \\<artist\\> - \\<song\\>` - Get track details

**🔍 Search:**
• `/search_artist \\<name\\>` - Search for artists
• `/search_track \\<query\\>` - Search for tracks
• `/similar \\<artist\\> - \\<song\\>` - Find similar songs

**📊 Charts (Shazam Data):**
• `/top_artist \\<name\\>` - Top tracks by artist
• `/top_world` - Global top tracks
• `/top_genre \\<genre\\>` - Top tracks by genre
• `/charts` - Show available chart options

**ℹ️ Other:**
• `/help` - Show this help message
• `/start` - Welcome message

**💡 Tips:**
- Send audio files for instant Shazam recognition!
- Use format "Artist - Song" for track commands
- Available genres: pop, rock, electronic, hip-hop, etc.

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

        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("artist", self.get_artist_info))
        application.add_handler(CommandHandler("track", self.get_track_info))
        application.add_handler(CommandHandler("search_artist", self.search_artists))
        application.add_handler(CommandHandler("search_track", self.search_tracks))
        application.add_handler(CommandHandler("top_artist", self.get_top_artist_tracks))
        application.add_handler(CommandHandler("top_world", self.get_top_world_tracks))
        application.add_handler(CommandHandler("top_genre", self.get_top_genre_tracks))
        application.add_handler(CommandHandler("similar", self.get_similar_songs))
        application.add_handler(CommandHandler("charts", self.get_charts))
        
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