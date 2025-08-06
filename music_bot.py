import os
import logging
import asyncio
import aiofiles
from typing import Dict, List, Optional, Any
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

import requests
from shazamio import Shazam
import pylast
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MusicBot:
    def __init__(self):
        # Initialize APIs
        self.shazam = Shazam()
        
        # Last.fm API
        self.lastfm_api_key = os.getenv('LASTFM_API_KEY')
        self.lastfm_api_secret = os.getenv('LASTFM_API_SECRET')
        if self.lastfm_api_key and self.lastfm_api_secret:
            self.lastfm_network = pylast.LastFMNetwork(
                api_key=self.lastfm_api_key,
                api_secret=self.lastfm_api_secret
            )
        else:
            self.lastfm_network = None
            
        # Spotify API
        spotify_client_id = os.getenv('SPOTIFY_CLIENT_ID')
        spotify_client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
        if spotify_client_id and spotify_client_secret:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=spotify_client_id,
                client_secret=spotify_client_secret
            )
            self.spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)
        else:
            self.spotify = None

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Start command handler"""
        welcome_message = """
🎵 Welcome to the Music Bot! 🎵

Here's what I can do for you:

🔎🎵 **Recognize track** - Send me an audio file and I'll identify the song
👨‍🎤 **About artist** - /artist <artist_name>
🎵📄 **About track** - /track <artist> - <song>
🎵⌛ **Track listening count** - /listens <artist> - <song>
🎶💬 **Similar songs** - /similar <artist> - <song>
🔎👨‍🎤 **Search artists** - /search_artist <name>
🔎🎶 **Search tracks** - /search_track <query>
🔝🎶👨‍🎤 **Top artist tracks** - /top_artist <artist_name>
🔝🎶🏙️ **Top tracks in city** - /top_city <city_name>
🔝🎶🏳️‍🌈 **Top tracks in country** - /top_country <country_name>
🔝🎶🏳️‍🌈🎸 **Top tracks by genre in country** - /top_country_genre <country> <genre>
🔝🎶🌏🎸 **Top tracks by genre worldwide** - /top_genre <genre>
🔝🎶🌏 **Top tracks worldwide** - /top_world

Send me an audio file to start recognizing music! 🎧
        """
        await update.message.reply_text(welcome_message)

    async def recognize_audio(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Recognize track from audio file"""
        try:
            if not update.message.audio and not update.message.voice and not update.message.video_note:
                await update.message.reply_text("Please send an audio file for music recognition! 🎵")
                return

            await update.message.reply_text("🔍 Analyzing your audio file... This may take a moment!")

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
                
                # Format the response
                title = track_info.get('title', 'Unknown')
                artist = track_info.get('subtitle', 'Unknown Artist')
                
                response = f"🎵 **Track Recognized!**\n\n"
                response += f"🎼 **Title:** {title}\n"
                response += f"👨‍🎤 **Artist:** {artist}\n"
                
                if 'sections' in track_info:
                    for section in track_info['sections']:
                        if section.get('type') == 'SONG':
                            metadata = section.get('metadata', [])
                            for meta in metadata:
                                if meta.get('title') == 'Album':
                                    response += f"💿 **Album:** {meta.get('text', 'Unknown')}\n"
                                elif meta.get('title') == 'Released':
                                    response += f"📅 **Released:** {meta.get('text', 'Unknown')}\n"
                
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
        """Get information about an artist"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /artist <artist_name>")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching for information about {artist_name}...")

        try:
            # Get artist info from Shazam
            artists = await self.shazam.search_artist(artist_name)
            
            if not artists or 'artists' not in artists or not artists['artists']['hits']:
                await update.message.reply_text(f"❌ Sorry, I couldn't find information about '{artist_name}'")
                return

            artist_data = artists['artists']['hits'][0]['artist']
            
            response = f"👨‍🎤 **Artist Information**\n\n"
            response += f"🎵 **Name:** {artist_data.get('name', 'Unknown')}\n"
            
            if 'avatar' in artist_data:
                response += f"🖼️ **Avatar:** Available\n"
            
            # Get additional info from Last.fm if available
            if self.lastfm_network:
                try:
                    lastfm_artist = self.lastfm_network.get_artist(artist_name)
                    bio = lastfm_artist.get_bio_summary()
                    if bio:
                        response += f"\n📖 **Biography:**\n{bio[:500]}...\n"
                    
                    listeners = lastfm_artist.get_listener_count()
                    if listeners:
                        response += f"👥 **Listeners:** {listeners:,}\n"
                        
                    playcount = lastfm_artist.get_playcount()
                    if playcount:
                        response += f"▶️ **Total Plays:** {playcount:,}\n"
                        
                except Exception as e:
                    logger.error(f"Last.fm artist error: {e}")

            # Add action buttons
            keyboard = [
                [InlineKeyboardButton("🔝 Top Tracks", callback_data=f"top_artist_{artist_name}")],
                [InlineKeyboardButton("🎶 Similar Artists", callback_data=f"similar_artist_{artist_name}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Artist info error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching artist information.")

    async def get_track_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get information about a track"""
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

        await update.message.reply_text(f"🔍 Searching for '{track}' by {artist}...")

        try:
            # Search for the track using Shazam
            search_results = await self.shazam.search_track(f"{artist} {track}")
            
            response = f"🎵 **Track Information**\n\n"
            response += f"🎼 **Title:** {track}\n"
            response += f"👨‍🎤 **Artist:** {artist}\n"

            if search_results and 'tracks' in search_results and search_results['tracks']['hits']:
                track_data = search_results['tracks']['hits'][0]['track']
                
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

            # Get additional info from Last.fm if available
            if self.lastfm_network:
                try:
                    lastfm_track = self.lastfm_network.get_track(artist, track)
                    
                    duration = lastfm_track.get_duration()
                    if duration:
                        minutes = duration // 60000
                        seconds = (duration % 60000) // 1000
                        response += f"⏱️ **Duration:** {minutes}:{seconds:02d}\n"
                    
                    playcount = lastfm_track.get_playcount()
                    if playcount:
                        response += f"▶️ **Play Count:** {playcount:,}\n"
                        
                    listeners = lastfm_track.get_listener_count()
                    if listeners:
                        response += f"👥 **Listeners:** {listeners:,}\n"
                        
                except Exception as e:
                    logger.error(f"Last.fm track error: {e}")

            # Add action buttons
            keyboard = [
                [InlineKeyboardButton("🎶 Similar Songs", callback_data=f"similar_{artist}_{track}")],
                [InlineKeyboardButton("👨‍🎤 About Artist", callback_data=f"artist_{artist}")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(response, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Track info error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching track information.")

    async def get_track_listens(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get listening count for a track"""
        if len(context.args) < 3 or '-' not in ' '.join(context.args):
            await update.message.reply_text("Please provide artist and track! Usage: /listens <artist> - <song>")
            return

        query = ' '.join(context.args)
        try:
            artist, track = query.split(' - ', 1)
            artist = artist.strip()
            track = track.strip()
        except ValueError:
            await update.message.reply_text("Please use the format: /listens <artist> - <song>")
            return

        await update.message.reply_text(f"🔍 Getting listening statistics for '{track}' by {artist}...")

        try:
            response = f"🎵⌛ **Listening Statistics**\n\n"
            response += f"🎼 **Track:** {track}\n"
            response += f"👨‍🎤 **Artist:** {artist}\n\n"

            # Get stats from Last.fm
            if self.lastfm_network:
                try:
                    lastfm_track = self.lastfm_network.get_track(artist, track)
                    
                    playcount = lastfm_track.get_playcount()
                    if playcount:
                        response += f"▶️ **Total Plays:** {playcount:,}\n"
                    
                    listeners = lastfm_track.get_listener_count()
                    if listeners:
                        response += f"👥 **Total Listeners:** {listeners:,}\n"
                    
                    # Calculate average plays per listener
                    if playcount and listeners and listeners > 0:
                        avg_plays = playcount / listeners
                        response += f"📊 **Avg Plays per Listener:** {avg_plays:.1f}\n"
                        
                except Exception as e:
                    logger.error(f"Last.fm listens error: {e}")
                    response += "❌ Unable to fetch listening statistics from Last.fm\n"
            else:
                response += "❌ Last.fm API not configured for detailed statistics\n"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Track listens error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching listening statistics.")

    async def get_similar_songs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get similar songs"""
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

        await update.message.reply_text(f"🔍 Finding songs similar to '{track}' by {artist}...")

        try:
            response = f"🎶💬 **Similar Songs**\n\n"
            response += f"Based on: {track} by {artist}\n\n"

            similar_found = False

            # Get similar tracks from Last.fm
            if self.lastfm_network:
                try:
                    lastfm_track = self.lastfm_network.get_track(artist, track)
                    similar_tracks = lastfm_track.get_similar(limit=10)
                    
                    if similar_tracks:
                        for i, similar_track in enumerate(similar_tracks[:5], 1):
                            similarity = similar_track.match * 100
                            response += f"{i}. 🎵 **{similar_track.item.title}**\n"
                            response += f"   👨‍🎤 by {similar_track.item.artist}\n"
                            response += f"   📊 Similarity: {similarity:.1f}%\n\n"
                        similar_found = True
                        
                except Exception as e:
                    logger.error(f"Last.fm similar error: {e}")

            # Try Spotify recommendations if available
            if self.spotify and not similar_found:
                try:
                    # Search for the track on Spotify
                    results = self.spotify.search(q=f"artist:{artist} track:{track}", type='track', limit=1)
                    if results['tracks']['items']:
                        track_id = results['tracks']['items'][0]['id']
                        
                        # Get recommendations
                        recommendations = self.spotify.recommendations(seed_tracks=[track_id], limit=5)
                        
                        for i, rec_track in enumerate(recommendations['tracks'], 1):
                            artists = ', '.join([artist['name'] for artist in rec_track['artists']])
                            response += f"{i}. 🎵 **{rec_track['name']}**\n"
                            response += f"   👨‍🎤 by {artists}\n"
                            response += f"   💿 Album: {rec_track['album']['name']}\n\n"
                        similar_found = True
                        
                except Exception as e:
                    logger.error(f"Spotify recommendations error: {e}")

            if not similar_found:
                response += "❌ Unable to find similar songs. Try checking the artist and track name."

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Similar songs error: {e}")
            await update.message.reply_text("❌ An error occurred while finding similar songs.")

    async def search_artists(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for artists"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /search_artist <name>")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching for artists matching '{artist_name}'...")

        try:
            # Search using Shazam
            artists = await self.shazam.search_artist(artist_name)
            
            if not artists or 'artists' not in artists or not artists['artists']['hits']:
                await update.message.reply_text(f"❌ No artists found matching '{artist_name}'")
                return

            response = f"🔎👨‍🎤 **Artist Search Results**\n\n"
            response += f"Search query: {artist_name}\n\n"

            for i, hit in enumerate(artists['artists']['hits'][:5], 1):
                artist_data = hit['artist']
                name = artist_data.get('name', 'Unknown')
                response += f"{i}. 👨‍🎤 **{name}**\n"
                
                if 'adamid' in artist_data:
                    response += f"   🆔 ID: {artist_data['adamid']}\n"
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
            await update.message.reply_text("❌ An error occurred while searching for artists.")

    async def search_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Search for tracks"""
        if not context.args:
            await update.message.reply_text("Please provide a search query! Usage: /search_track <query>")
            return

        query = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Searching for tracks matching '{query}'...")

        try:
            # Search using Shazam
            tracks = await self.shazam.search_track(query)
            
            if not tracks or 'tracks' not in tracks or not tracks['tracks']['hits']:
                await update.message.reply_text(f"❌ No tracks found matching '{query}'")
                return

            response = f"🔎🎶 **Track Search Results**\n\n"
            response += f"Search query: {query}\n\n"

            for i, hit in enumerate(tracks['tracks']['hits'][:5], 1):
                track_data = hit['track']
                title = track_data.get('title', 'Unknown')
                artist = track_data.get('subtitle', 'Unknown Artist')
                
                response += f"{i}. 🎵 **{title}**\n"
                response += f"   👨‍🎤 by {artist}\n"
                
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
            await update.message.reply_text("❌ An error occurred while searching for tracks.")

    async def get_top_artist_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks for an artist"""
        if not context.args:
            await update.message.reply_text("Please provide an artist name! Usage: /top_artist <artist_name>")
            return

        artist_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Getting top tracks for {artist_name}...")

        try:
            response = f"🔝🎶👨‍🎤 **Top Tracks**\n\n"
            response += f"Artist: {artist_name}\n\n"

            tracks_found = False

            # Get top tracks from Last.fm
            if self.lastfm_network:
                try:
                    lastfm_artist = self.lastfm_network.get_artist(artist_name)
                    top_tracks = lastfm_artist.get_top_tracks(limit=10)
                    
                    if top_tracks:
                        for i, track in enumerate(top_tracks[:5], 1):
                            playcount = track.item.get_playcount()
                            response += f"{i}. 🎵 **{track.item.title}**\n"
                            if playcount:
                                response += f"   ▶️ Plays: {playcount:,}\n"
                            response += "\n"
                        tracks_found = True
                        
                except Exception as e:
                    logger.error(f"Last.fm top tracks error: {e}")

            # Try Spotify if Last.fm failed
            if self.spotify and not tracks_found:
                try:
                    results = self.spotify.search(q=f"artist:{artist_name}", type='artist', limit=1)
                    if results['artists']['items']:
                        artist_id = results['artists']['items'][0]['id']
                        top_tracks = self.spotify.artist_top_tracks(artist_id)
                        
                        for i, track in enumerate(top_tracks['tracks'][:5], 1):
                            popularity = track.get('popularity', 0)
                            response += f"{i}. 🎵 **{track['name']}**\n"
                            response += f"   📊 Popularity: {popularity}/100\n"
                            response += f"   💿 Album: {track['album']['name']}\n\n"
                        tracks_found = True
                        
                except Exception as e:
                    logger.error(f"Spotify top tracks error: {e}")

            if not tracks_found:
                response += "❌ Unable to fetch top tracks. Please check the artist name."

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top artist tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching top tracks.")

    async def get_top_city_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks in a city"""
        if not context.args:
            await update.message.reply_text("Please provide a city name! Usage: /top_city <city_name>")
            return

        city_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Getting top tracks in {city_name}...")

        try:
            response = f"🔝🎶🏙️ **Top Tracks in {city_name}**\n\n"

            # Note: Real-time city charts require specific APIs that may not be freely available
            # This is a simulation using Last.fm's geo.getTopTracks if available
            if self.lastfm_network:
                try:
                    # Last.fm doesn't have city-specific charts, so we'll use country charts as fallback
                    response += "🔄 *Using regional approximation*\n\n"
                    
                    # For demo purposes, showing popular tracks
                    chart = self.lastfm_network.get_top_tracks(limit=5)
                    
                    for i, track in enumerate(chart, 1):
                        artist = track.item.artist.name if track.item.artist else "Unknown Artist"
                        title = track.item.title
                        playcount = track.item.get_playcount()
                        
                        response += f"{i}. 🎵 **{title}**\n"
                        response += f"   👨‍🎤 by {artist}\n"
                        if playcount:
                            response += f"   ▶️ Plays: {playcount:,}\n"
                        response += "\n"
                        
                except Exception as e:
                    logger.error(f"Last.fm city charts error: {e}")
                    response += "❌ Unable to fetch city-specific charts at this time.\n"
                    response += "This feature requires specialized geo-location music APIs."
            else:
                response += "❌ Music API not configured for geo-location charts."

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top city tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching city charts.")

    async def get_top_country_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks in a country"""
        if not context.args:
            await update.message.reply_text("Please provide a country name! Usage: /top_country <country_name>")
            return

        country_name = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Getting top tracks in {country_name}...")

        try:
            response = f"🔝🎶🏳️‍🌈 **Top Tracks in {country_name}**\n\n"

            tracks_found = False

            # Get country charts from Last.fm
            if self.lastfm_network:
                try:
                    # Last.fm uses country codes, so we'll try common ones
                    country_codes = {
                        'united states': 'US', 'usa': 'US', 'america': 'US',
                        'united kingdom': 'GB', 'uk': 'GB', 'britain': 'GB',
                        'germany': 'DE', 'france': 'FR', 'italy': 'IT',
                        'spain': 'ES', 'canada': 'CA', 'australia': 'AU',
                        'japan': 'JP', 'brazil': 'BR', 'russia': 'RU',
                        'india': 'IN', 'china': 'CN', 'south korea': 'KR'
                    }
                    
                    country_code = country_codes.get(country_name.lower())
                    if country_code:
                        # Use global charts as Last.fm's geo charts are limited
                        chart = self.lastfm_network.get_top_tracks(limit=5)
                        
                        response += f"🌍 *Global trending tracks (representative for {country_name})*\n\n"
                        
                        for i, track in enumerate(chart, 1):
                            artist = track.item.artist.name if track.item.artist else "Unknown Artist"
                            title = track.item.title
                            playcount = track.item.get_playcount()
                            
                            response += f"{i}. 🎵 **{title}**\n"
                            response += f"   👨‍🎤 by {artist}\n"
                            if playcount:
                                response += f"   ▶️ Plays: {playcount:,}\n"
                            response += "\n"
                        tracks_found = True
                    else:
                        response += f"❌ Country '{country_name}' not found in supported regions.\n"
                        response += "Try: USA, UK, Germany, France, Italy, Spain, Canada, Australia, Japan, Brazil"
                        
                except Exception as e:
                    logger.error(f"Last.fm country charts error: {e}")
                    response += "❌ Unable to fetch country charts."

            if not tracks_found and not country_codes.get(country_name.lower()):
                response += "\n📝 Supported countries: USA, UK, Germany, France, Italy, Spain, Canada, Australia, Japan, Brazil, Russia, India, China, South Korea"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top country tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching country charts.")

    async def get_top_country_genre_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks in country by genre"""
        if len(context.args) < 2:
            await update.message.reply_text("Please provide country and genre! Usage: /top_country_genre <country> <genre>")
            return

        country_name = context.args[0]
        genre = ' '.join(context.args[1:])
        await update.message.reply_text(f"🔍 Getting top {genre} tracks in {country_name}...")

        try:
            response = f"🔝🎶🏳️‍🌈🎸 **Top {genre.title()} Tracks in {country_name}**\n\n"

            tracks_found = False

            # Get genre-specific tracks from Last.fm
            if self.lastfm_network:
                try:
                    # Get top tracks for the genre
                    tag = self.lastfm_network.get_tag(genre)
                    top_tracks = tag.get_top_tracks(limit=5)
                    
                    if top_tracks:
                        response += f"🎸 Genre: {genre.title()}\n"
                        response += f"🏳️‍🌈 Region: {country_name}\n\n"
                        
                        for i, track in enumerate(top_tracks, 1):
                            artist = track.item.artist.name if track.item.artist else "Unknown Artist"
                            title = track.item.title
                            
                            response += f"{i}. 🎵 **{title}**\n"
                            response += f"   👨‍🎤 by {artist}\n"
                            response += f"   🎸 Genre: {genre.title()}\n\n"
                        tracks_found = True
                    else:
                        response += f"❌ No tracks found for genre '{genre}'"
                        
                except Exception as e:
                    logger.error(f"Last.fm genre charts error: {e}")
                    response += f"❌ Unable to fetch charts for genre '{genre}'"

            # Try Spotify if Last.fm failed
            if self.spotify and not tracks_found:
                try:
                    # Search for tracks by genre
                    results = self.spotify.search(q=f"genre:{genre}", type='track', limit=5)
                    
                    if results['tracks']['items']:
                        response += f"🎸 Genre: {genre.title()}\n"
                        response += f"🏳️‍🌈 Region: {country_name} (Global results)\n\n"
                        
                        for i, track in enumerate(results['tracks']['items'], 1):
                            artists = ', '.join([artist['name'] for artist in track['artists']])
                            popularity = track.get('popularity', 0)
                            
                            response += f"{i}. 🎵 **{track['name']}**\n"
                            response += f"   👨‍🎤 by {artists}\n"
                            response += f"   📊 Popularity: {popularity}/100\n\n"
                        tracks_found = True
                        
                except Exception as e:
                    logger.error(f"Spotify genre search error: {e}")

            if not tracks_found:
                response += "\n📝 Popular genres: rock, pop, hip-hop, electronic, jazz, classical, country, r&b, indie, metal"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top country genre tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching genre charts.")

    async def get_top_world_genre_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks worldwide by genre"""
        if not context.args:
            await update.message.reply_text("Please provide a genre! Usage: /top_genre <genre>")
            return

        genre = ' '.join(context.args)
        await update.message.reply_text(f"🔍 Getting top {genre} tracks worldwide...")

        try:
            response = f"🔝🎶🌏🎸 **Top {genre.title()} Tracks Worldwide**\n\n"

            tracks_found = False

            # Get genre tracks from Last.fm
            if self.lastfm_network:
                try:
                    tag = self.lastfm_network.get_tag(genre)
                    top_tracks = tag.get_top_tracks(limit=5)
                    
                    if top_tracks:
                        for i, track in enumerate(top_tracks, 1):
                            artist = track.item.artist.name if track.item.artist else "Unknown Artist"
                            title = track.item.title
                            
                            response += f"{i}. 🎵 **{title}**\n"
                            response += f"   👨‍🎤 by {artist}\n"
                            response += f"   🎸 Genre: {genre.title()}\n\n"
                        tracks_found = True
                        
                except Exception as e:
                    logger.error(f"Last.fm world genre error: {e}")

            # Try Spotify if Last.fm failed
            if self.spotify and not tracks_found:
                try:
                    results = self.spotify.search(q=f"genre:{genre}", type='track', limit=5)
                    
                    if results['tracks']['items']:
                        for i, track in enumerate(results['tracks']['items'], 1):
                            artists = ', '.join([artist['name'] for artist in track['artists']])
                            popularity = track.get('popularity', 0)
                            
                            response += f"{i}. 🎵 **{track['name']}**\n"
                            response += f"   👨‍🎤 by {artists}\n"
                            response += f"   📊 Popularity: {popularity}/100\n"
                            response += f"   💿 Album: {track['album']['name']}\n\n"
                        tracks_found = True
                        
                except Exception as e:
                    logger.error(f"Spotify world genre error: {e}")

            if not tracks_found:
                response += f"❌ No tracks found for genre '{genre}'\n\n"
                response += "📝 Popular genres: rock, pop, hip-hop, electronic, jazz, classical, country, r&b, indie, metal, folk, blues, reggae, punk, alternative"

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top world genre tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching global genre charts.")

    async def get_top_world_tracks(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Get top tracks worldwide"""
        await update.message.reply_text("🔍 Getting top tracks worldwide...")

        try:
            response = f"🔝🎶🌏 **Top Tracks Worldwide**\n\n"

            tracks_found = False

            # Get global charts from Last.fm
            if self.lastfm_network:
                try:
                    chart = self.lastfm_network.get_top_tracks(limit=10)
                    
                    if chart:
                        for i, track in enumerate(chart[:5], 1):
                            artist = track.item.artist.name if track.item.artist else "Unknown Artist"
                            title = track.item.title
                            playcount = track.item.get_playcount()
                            
                            response += f"{i}. 🎵 **{title}**\n"
                            response += f"   👨‍🎤 by {artist}\n"
                            if playcount:
                                response += f"   ▶️ Global Plays: {playcount:,}\n"
                            response += "\n"
                        tracks_found = True
                        
                except Exception as e:
                    logger.error(f"Last.fm world charts error: {e}")

            # Try Spotify global charts if Last.fm failed
            if self.spotify and not tracks_found:
                try:
                    # Search for currently popular tracks
                    results = self.spotify.search(q="year:2024", type='track', limit=5)
                    
                    if results['tracks']['items']:
                        response += "🌟 *Current popular tracks*\n\n"
                        
                        for i, track in enumerate(results['tracks']['items'], 1):
                            artists = ', '.join([artist['name'] for artist in track['artists']])
                            popularity = track.get('popularity', 0)
                            
                            response += f"{i}. 🎵 **{track['name']}**\n"
                            response += f"   👨‍🎤 by {artists}\n"
                            response += f"   📊 Popularity: {popularity}/100\n"
                            response += f"   💿 Album: {track['album']['name']}\n\n"
                        tracks_found = True
                        
                except Exception as e:
                    logger.error(f"Spotify world charts error: {e}")

            if not tracks_found:
                response += "❌ Unable to fetch global charts at this time."

            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

        except Exception as e:
            logger.error(f"Top world tracks error: {e}")
            await update.message.reply_text("❌ An error occurred while fetching global charts.")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()

        data = query.data
        
        try:
            if data.startswith("artist_"):
                artist_name = data[7:]
                await query.edit_message_text(f"🔍 Getting information about {artist_name}...")
                
                # Get artist info
                try:
                    artists = await self.shazam.search_artist(artist_name)
                    
                    if not artists or 'artists' not in artists or not artists['artists']['hits']:
                        await query.edit_message_text(f"❌ Sorry, I couldn't find information about '{artist_name}'")
                        return

                    artist_data = artists['artists']['hits'][0]['artist']
                    
                    response = f"👨‍🎤 **Artist Information**\n\n"
                    response += f"🎵 **Name:** {artist_data.get('name', 'Unknown')}\n"
                    
                    if 'avatar' in artist_data:
                        response += f"🖼️ **Avatar:** Available\n"
                    
                    # Get additional info from Last.fm if available
                    if self.lastfm_network:
                        try:
                            lastfm_artist = self.lastfm_network.get_artist(artist_name)
                            bio = lastfm_artist.get_bio_summary()
                            if bio:
                                response += f"\n📖 **Biography:**\n{bio[:500]}...\n"
                            
                            listeners = lastfm_artist.get_listener_count()
                            if listeners:
                                response += f"👥 **Listeners:** {listeners:,}\n"
                                
                            playcount = lastfm_artist.get_playcount()
                            if playcount:
                                response += f"▶️ **Total Plays:** {playcount:,}\n"
                                
                        except Exception as e:
                            logger.error(f"Last.fm artist error: {e}")

                    await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
                    
                except Exception as e:
                    logger.error(f"Artist info error: {e}")
                    await query.edit_message_text("❌ An error occurred while fetching artist information.")
                
            elif data.startswith("track_"):
                parts = data[6:].split("_", 1)
                if len(parts) == 2:
                    artist, track = parts
                    await query.edit_message_text(f"🔍 Getting information about '{track}' by {artist}...")
                    
                    try:
                        search_results = await self.shazam.search_track(f"{artist} {track}")
                        
                        response = f"🎵 **Track Information**\n\n"
                        response += f"🎼 **Title:** {track}\n"
                        response += f"👨‍🎤 **Artist:** {artist}\n"

                        if search_results and 'tracks' in search_results and search_results['tracks']['hits']:
                            track_data = search_results['tracks']['hits'][0]['track']
                            
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

                        # Get additional info from Last.fm if available
                        if self.lastfm_network:
                            try:
                                lastfm_track = self.lastfm_network.get_track(artist, track)
                                
                                duration = lastfm_track.get_duration()
                                if duration:
                                    minutes = duration // 60000
                                    seconds = (duration % 60000) // 1000
                                    response += f"⏱️ **Duration:** {minutes}:{seconds:02d}\n"
                                
                                playcount = lastfm_track.get_playcount()
                                if playcount:
                                    response += f"▶️ **Play Count:** {playcount:,}\n"
                                    
                                listeners = lastfm_track.get_listener_count()
                                if listeners:
                                    response += f"👥 **Listeners:** {listeners:,}\n"
                                    
                            except Exception as e:
                                logger.error(f"Last.fm track error: {e}")

                        await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
                        
                    except Exception as e:
                        logger.error(f"Track info error: {e}")
                        await query.edit_message_text("❌ An error occurred while fetching track information.")
                    
            elif data.startswith("similar_"):
                parts = data[8:].split("_", 1)
                if len(parts) == 2:
                    artist, track = parts
                    await query.edit_message_text(f"🔍 Finding songs similar to '{track}' by {artist}...")
                    
                    try:
                        response = f"🎶💬 **Similar Songs**\n\n"
                        response += f"Based on: {track} by {artist}\n\n"

                        similar_found = False

                        # Get similar tracks from Last.fm
                        if self.lastfm_network:
                            try:
                                lastfm_track = self.lastfm_network.get_track(artist, track)
                                similar_tracks = lastfm_track.get_similar(limit=10)
                                
                                if similar_tracks:
                                    for i, similar_track in enumerate(similar_tracks[:5], 1):
                                        similarity = similar_track.match * 100
                                        response += f"{i}. 🎵 **{similar_track.item.title}**\n"
                                        response += f"   👨‍🎤 by {similar_track.item.artist}\n"
                                        response += f"   📊 Similarity: {similarity:.1f}%\n\n"
                                    similar_found = True
                                    
                            except Exception as e:
                                logger.error(f"Last.fm similar error: {e}")

                        # Try Spotify recommendations if available
                        if self.spotify and not similar_found:
                            try:
                                # Search for the track on Spotify
                                results = self.spotify.search(q=f"artist:{artist} track:{track}", type='track', limit=1)
                                if results['tracks']['items']:
                                    track_id = results['tracks']['items'][0]['id']
                                    
                                    # Get recommendations
                                    recommendations = self.spotify.recommendations(seed_tracks=[track_id], limit=5)
                                    
                                    for i, rec_track in enumerate(recommendations['tracks'], 1):
                                        artists = ', '.join([artist['name'] for artist in rec_track['artists']])
                                        response += f"{i}. 🎵 **{rec_track['name']}**\n"
                                        response += f"   👨‍🎤 by {artists}\n"
                                        response += f"   💿 Album: {rec_track['album']['name']}\n\n"
                                    similar_found = True
                                    
                            except Exception as e:
                                logger.error(f"Spotify recommendations error: {e}")

                        if not similar_found:
                            response += "❌ Unable to find similar songs. Try checking the artist and track name."

                        await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
                        
                    except Exception as e:
                        logger.error(f"Similar songs error: {e}")
                        await query.edit_message_text("❌ An error occurred while finding similar songs.")
                    
            elif data.startswith("top_artist_"):
                artist_name = data[11:]
                await query.edit_message_text(f"🔍 Getting top tracks for {artist_name}...")
                
                try:
                    response = f"🔝🎶👨‍🎤 **Top Tracks**\n\n"
                    response += f"Artist: {artist_name}\n\n"

                    tracks_found = False

                    # Get top tracks from Last.fm
                    if self.lastfm_network:
                        try:
                            lastfm_artist = self.lastfm_network.get_artist(artist_name)
                            top_tracks = lastfm_artist.get_top_tracks(limit=10)
                            
                            if top_tracks:
                                for i, track in enumerate(top_tracks[:5], 1):
                                    playcount = track.item.get_playcount()
                                    response += f"{i}. 🎵 **{track.item.title}**\n"
                                    if playcount:
                                        response += f"   ▶️ Plays: {playcount:,}\n"
                                    response += "\n"
                                tracks_found = True
                                
                        except Exception as e:
                            logger.error(f"Last.fm top tracks error: {e}")

                    # Try Spotify if Last.fm failed
                    if self.spotify and not tracks_found:
                        try:
                            results = self.spotify.search(q=f"artist:{artist_name}", type='artist', limit=1)
                            if results['artists']['items']:
                                artist_id = results['artists']['items'][0]['id']
                                top_tracks = self.spotify.artist_top_tracks(artist_id)
                                
                                for i, track in enumerate(top_tracks['tracks'][:5], 1):
                                    popularity = track.get('popularity', 0)
                                    response += f"{i}. 🎵 **{track['name']}**\n"
                                    response += f"   📊 Popularity: {popularity}/100\n"
                                    response += f"   💿 Album: {track['album']['name']}\n\n"
                                tracks_found = True
                                
                        except Exception as e:
                            logger.error(f"Spotify top tracks error: {e}")

                    if not tracks_found:
                        response += "❌ Unable to fetch top tracks. Please check the artist name."

                    await query.edit_message_text(response, parse_mode=ParseMode.MARKDOWN)
                    
                except Exception as e:
                    logger.error(f"Top artist tracks error: {e}")
                    await query.edit_message_text("❌ An error occurred while fetching top tracks.")
                
        except Exception as e:
            logger.error(f"Button callback error: {e}")
            await query.edit_message_text("❌ An error occurred while processing your request.")

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Help command handler"""
        help_text = """
🎵 **Music Bot Commands** 🎵

**🔎 Recognition & Info:**
• Send audio file - Recognize track automatically
• `/artist <name>` - Get artist information
• `/track <artist> - <song>` - Get track details
• `/listens <artist> - <song>` - Get listening statistics

**🔍 Search:**
• `/search_artist <name>` - Search for artists
• `/search_track <query>` - Search for tracks
• `/similar <artist> - <song>` - Find similar songs

**📊 Charts & Top Lists:**
• `/top_artist <name>` - Top tracks by artist
• `/top_city <city>` - Top tracks in city
• `/top_country <country>` - Top tracks in country
• `/top_country_genre <country> <genre>` - Top tracks by genre in country
• `/top_genre <genre>` - Top tracks by genre worldwide
• `/top_world` - Global top tracks

**ℹ️ Other:**
• `/help` - Show this help message
• `/start` - Welcome message

**💡 Tips:**
- Send audio files for instant recognition!
- Use format "Artist - Song" for track commands
- Try popular genres: rock, pop, hip-hop, electronic, jazz
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
        application.add_handler(CommandHandler("listens", self.get_track_listens))
        application.add_handler(CommandHandler("similar", self.get_similar_songs))
        application.add_handler(CommandHandler("search_artist", self.search_artists))
        application.add_handler(CommandHandler("search_track", self.search_tracks))
        application.add_handler(CommandHandler("top_artist", self.get_top_artist_tracks))
        application.add_handler(CommandHandler("top_city", self.get_top_city_tracks))
        application.add_handler(CommandHandler("top_country", self.get_top_country_tracks))
        application.add_handler(CommandHandler("top_country_genre", self.get_top_country_genre_tracks))
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
        logger.info("Starting Music Bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    bot = MusicBot()
    bot.run()