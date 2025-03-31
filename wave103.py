#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wave103.py
Discord bot for playing audio from YouTube in voice channels. The bot uses the
yt-dlp library to search for and stream audio from YouTube videos.

To install the required libraries, run:
    pip install discord.py yt-dlp

Created: 2025-03-20 21:29:39 (UTC)
Author: rinmz
"""

import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix = '!',
    description = "Plays songs from YouTube based on user commands",
    intents = intents
)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0'
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(YTDL_OPTIONS)

queue = []


def search_youtube(query: str) -> dict:
    """
    Searches YouTube for the given query and returns the first result.
    
    Args:
        query (str): The name of the song or search query.
    
    Returns:
        dict: A dictionary containing information about the video result.
    """
    try:
        info = ytdl.extract_info(query, download=False)
        if 'entries' in info:
            return info['entries'][0]
        return info
    except Exception as e:
        print(f"Error during YouTube search: {e}")
        return None


class YTDLSource(discord.PCMVolumeTransformer):
    """
    A class that creates an audio stream source from youtube_dl data.
    """
    def __init__(self, source, *, data, volume = 0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url: str, *, loop=None, stream: bool = False):
        """
        Asynchronously creates an audio source from the given URL.
        
        Args:
            url (str): The YouTube video URL or search query.
            loop (asyncio.AbstractEventLoop, optional): The event loop to use. Defaults to the current loop.
            stream (bool, optional): Whether to stream the audio directly without downloading. Defaults to False.
        
        Returns:
            YTDLSource: An instance of YTDLSource containing the audio stream.
        """
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download = not stream))
        
        if 'entries' in data:
            data = data['entries'][0]
        
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data = data)


@bot.event
async def on_ready():
    """
    Event that is called when the bot successfully connects to Discord.
    """
    print(f'Logged in as {bot.user}')


@bot.command(name = 'play', help = 'Plays the specified song in the voice channel. Usage: !play <song name>')
async def play(ctx, *, query: str):
    """
    The !play command: Searches YouTube for the user-provided query,
    connects to the user's voice channel, and starts playing the song.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
        query (str): The song name or search query provided by the user.
    """
    if ctx.author.voice is None:
        embed = discord.Embed(description = "Please join a voice channel!")
        await ctx.send(embed = embed)
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    video_data = await ctx.bot.loop.run_in_executor(None, search_youtube, query)
    embed = discord.Embed(title = 'Added to queue:', description = f"**{video_data['title']}**")
    await ctx.send(embed = embed)

    if video_data is None:
        embed = discord.Embed(description = "Either we couldn't find this song or it might not appeal to the Vice City vibe.")
        await ctx.send(embed=embed)
        return

    queue.append(video_data)

    if not ctx.voice_client.is_playing():
        await play_next(ctx)


@bot.command(name = 'play_next', help = 'Plays the next song in the queue.')
async def play_next(ctx):
    if len(queue) > 0:
        video_data = queue.pop(0)
        source = await YTDLSource.from_url(video_data['url'], loop=ctx.bot.loop, stream=True)
        
        def after_playing(error):
            if error:
                print(f'Error: {error}')
            else:
                ctx.bot.loop.create_task(play_next(ctx))
        
        ctx.voice_client.play(source, after=after_playing)
        
        embed = discord.Embed(
            title=f"**{video_data['title']}**",
            url=video_data['webpage_url'],
            description=f"{video_data['uploader']}"
        )
        embed.set_thumbnail(url=video_data['thumbnail'])
        await ctx.send(embed=embed)


@bot.command(name = 'skip', help = 'Skips the current song and plays the next song in the queue.')
async def skip(ctx):
    """
    The !skip command: Skips the current song and plays the next song in the queue.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
    """
    if ctx.author.voice is None:
        embed = discord.Embed(description = "You are not in a voice channel!")
        await ctx.send(embed = embed)
        return

    if ctx.voice_client is None:
        embed = discord.Embed(description = "The bot is not connected to a voice channel.")
        await ctx.send(embed = embed)
        return

    if len(queue) == 0:
        embed = discord.Embed(description = "The queue is empty. If you want to stop the current song, use the !stop command.")
        await ctx.send(embed = embed)
        return

    if ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        embed = discord.Embed(description = "Skipping the current song.")
        await ctx.send(embed = embed)
    else:
        embed = discord.Embed(description = "The bot is not playing anything.")
        await ctx.send(embed = embed)


@bot.command(name = 'current', help = 'Displays the current song playing.')
async def current_song(ctx):
    """
    The !current command: Displays the current song playing.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
    """
    if ctx.voice_client.is_playing():
        embed = discord.Embed(title = "Currently Playing:")
        embed.add_field(name = f"{ctx.voice_client.source.title}", value = "", inline = False)
        await ctx.send(embed = embed)
    else:
        embed = discord.Embed(description = "The bot is not playing anything.")
        await ctx.send(embed = embed)


@bot.command(name = 'queue', help = 'Displays the current song queue.')
async def queue_info(ctx):
    """
    The !queue command: Displays the current song queue.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
    """
    if len(queue) == 0:
        embed = discord.Embed(description = "The queue is empty.")
        await ctx.send(embed = embed)
        return

    embed = discord.Embed(title = "Current Song Queue:")
    for i, video_data in enumerate(queue):
        embed.add_field(name = f"{i + 1}. {video_data['title']}", value = "", inline = False)
        
    await ctx.send(embed = embed)

@bot.command(name = 'remove', help = 'Removes a song from the queue. Usage: !remove <song number>')
async def remove_song(ctx, song_number: int):
    """
    The !remove command: Removes a song from the queue.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
        song_number (int): The number of the song to remove.
    """
    if song_number is None:
        embed = discord.Embed(description="Please provide a song number. Usage: !remove <song number>")
        await ctx.send(embed=embed)
        return
    
    if len(queue) == 0:
        embed = discord.Embed(description = "The queue is empty.")
        await ctx.send(embed = embed)
        return

    if song_number < 1 or song_number > len(queue):
        embed = discord.Embed(description = "Invalid song number.")
        await ctx.send(embed = embed)
        return

    removed_song = queue.pop(song_number - 1)
    embed = discord.Embed(description = f"**{removed_song['title']}** has been removed from the queue.")
    await ctx.send(embed = embed)

@bot.command(name = 'clear', help = 'Clears the current song queue.')
async def clear_queue(ctx):
    """
    The !clear command: Clears the current song queue.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
    """
    queue.clear()
    embed = discord.Embed(description = "The queue has been cleared.")
    await ctx.send(embed = embed)


@bot.command(name = 'pause', help = 'Pauses the current song.')
async def pause(ctx):
    """
    The !pause command: Pauses the current song.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
    """
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        embed = discord.Embed(description = "Pausing the current song.")
        await ctx.send(embed = embed)
    else:
        embed = discord.Embed(description = "The bot is not playing anything.")
        await ctx.send(embed = embed)


@bot.command(name = 'resume', help = 'Resumes the current song.')
async def resume(ctx):
    """
    The !resume command: Resumes the current song.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
    """
    if ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        embed = discord.Embed(description = "Resuming the current song.")
        await ctx.send(embed = embed)
    else:
        embed = discord.Embed(description = "The bot is not paused.")
        await ctx.send(embed = embed)


@bot.command(name = 'volume', help = 'Changes the volume of the bot. Usage: !volume <volume>')
async def volume(ctx, volume: int):
    """
    The !volume command: Changes the volume of the bot.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
        volume (int): The volume level to set.
    """
    if ctx.voice_client is None:
        embed = discord.Embed(description = "The bot is not in a voice channel.")
        await ctx.send(embed = embed)
        return

    ctx.voice_client.source.volume = volume / 100
    embed = discord.Embed(description = f"Setting the volume to {volume}.")
    await ctx.send(embed = embed)


@bot.command(name = 'stop', help = 'Disconnects the bot from the voice channel.')
async def stop(ctx):
    """
    The !stop command: Disconnects the bot from the voice channel and stops playback.
    
    Args:
        ctx (commands.Context): The context in which the command was invoked.
    """
    if ctx.voice_client is not None:
        await ctx.voice_client.disconnect()
        embed = discord.Embed(description = "Disconnecting from voice channel.")
        await ctx.send(embed = embed)
    else:
        embed = discord.Embed(description = "The bot is not in a voice channel.")
        await ctx.send(embed = embed)


if __name__ == '__main__':
    with open('token.txt', 'r') as file:
        TOKEN = file.read().strip()

    bot.run(TOKEN)