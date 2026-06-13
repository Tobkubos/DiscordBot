"""
Example: Integrating the Deepfake Detection Backend with Discord Bot

This example shows how to call the backend API from a Discord bot.
"""

import discord
from discord.ext import commands
import httpx
import asyncio
from typing import Optional

# Backend configuration
BACKEND_URL = "http://127.0.0.1:8000"
BACKEND_TIMEOUT = 60  # seconds


class DeepfakeDetector(commands.Cog):
    """Discord bot cog for deepfake detection."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.backend_url = BACKEND_URL
        self.http_client = None
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize HTTP client when bot is ready."""
        if self.http_client is None:
            self.http_client = httpx.AsyncClient(timeout=BACKEND_TIMEOUT)
        print(f"Deepfake detector loaded - Backend: {self.backend_url}")
    
    async def analyze_url(self, file_url: str, model: str = "mock") -> Optional[dict]:
        """
        Send a file URL to the backend for deepfake analysis.
        
        Args:
            file_url: URL of the file to analyze
            model: Model to use for detection
            
        Returns:
            Analysis result or None if failed
        """
        try:
            if self.http_client is None:
                self.http_client = httpx.AsyncClient(timeout=BACKEND_TIMEOUT)
            
            response = await self.http_client.post(
                f"{self.backend_url}/analyze",
                json={"file_url": file_url, "model": model},
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Backend error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Failed to analyze: {e}")
            return None
    
    @commands.command(name="deepfake_check")
    async def deepfake_check(self, ctx: commands.Context, url: str):
        """
        Check if a file at the given URL is a deepfake.
        
        Usage:
            !deepfake_check https://example.com/video.mp4
        """
        # Validate URL format
        if not url.startswith(("http://", "https://")):
            await ctx.send("❌ Invalid URL. Please provide a valid HTTP(S) URL.")
            return
        
        # Show loading message
        async with ctx.typing():
            # Check if backend is running
            try:
                health_response = await self.http_client.get(f"{self.backend_url}/")
                if health_response.status_code != 200:
                    await ctx.send("❌ Backend service is not responding. Please try again later.")
                    return
            except Exception as e:
                await ctx.send(f"❌ Cannot connect to backend service: {e}")
                return
            
            # Analyze the file
            await ctx.send(f"🔍 Analyzing file from: {url}\nThis may take a moment...")
            
            result = await self.analyze_url(url)
            
            if result is None:
                await ctx.send("❌ Analysis failed. Please check the URL and try again.")
                return
        
        # Format and display results
        is_deepfake = result["is_deepfake"]
        confidence = result["confidence"]
        analysis_time = result["analysis_time"]
        model_used = result.get("model_used", "unknown")
        
        # Create embed for nice formatting
        embed = discord.Embed(
            title="🔬 Deepfake Detection Result",
            color=discord.Color.red() if is_deepfake else discord.Color.green(),
        )
        
        embed.add_field(
            name="Detection Result",
            value="⚠️ **DEEPFAKE DETECTED**" if is_deepfake else "✅ **AUTHENTIC**",
            inline=False,
        )
        
        embed.add_field(
            name="Confidence",
            value=f"{confidence:.1%}",
            inline=True,
        )
        
        embed.add_field(
            name="Analysis Time",
            value=f"{analysis_time:.2f}s",
            inline=True,
        )
        
        embed.add_field(
            name="Model Used",
            value=model_used,
            inline=True,
        )
        
        embed.set_footer(text="Analysis performed by Deepfake Detection Service")
        
        await ctx.send(embed=embed)
    
    @commands.command(name="backend_status")
    async def backend_status(self, ctx: commands.Context):
        """Check the status of the deepfake detection backend."""
        try:
            async with ctx.typing():
                response = await self.http_client.get(f"{self.backend_url}/")
                
                if response.status_code == 200:
                    data = response.json()
                    embed = discord.Embed(
                        title="🟢 Backend Status",
                        color=discord.Color.green(),
                    )
                    embed.add_field(
                        name="Service",
                        value=data["service"],
                        inline=True,
                    )
                    embed.add_field(
                        name="Version",
                        value=data["version"],
                        inline=True,
                    )
                    embed.add_field(
                        name="Available Models",
                        value=", ".join(data["available_models"]),
                        inline=False,
                    )
                    await ctx.send(embed=embed)
                else:
                    await ctx.send("❌ Backend is not responding properly.")
        except Exception as e:
            await ctx.send(f"❌ Cannot connect to backend: {e}")
    
    async def cog_unload(self):
        """Cleanup when cog is unloaded."""
        if self.http_client:
            await self.http_client.aclose()


# Setup function to add this cog to your bot
async def setup(bot: commands.Bot):
    """Add the deepfake detector cog to the bot."""
    await bot.add_cog(DeepfakeDetector(bot))


# ============================================================================
# EXAMPLE BOT IMPLEMENTATION
# ============================================================================

# If you want to use this as a standalone bot, here's how:

# bot = commands.Bot(command_prefix="!", intents=discord.Intents.default())

# @bot.event
# async def on_ready():
#     print(f"Bot logged in as {bot.user}")

# async def main():
#     async with bot:
#         await setup(bot)
#         await bot.start("YOUR_BOT_TOKEN")

# if __name__ == "__main__":
#     asyncio.run(main())

# ============================================================================
# USAGE IN YOUR BOT
# ============================================================================

# 1. Save this file as: discord_bot_example.py or similar
# 
# 2. In your main bot file, add:
#    
#    from discord_bot_example import setup
#    
#    async def main():
#        async with bot:
#            await setup(bot)  # Load the deepfake detector cog
#            await bot.start(TOKEN)
#
# 3. Start the backend server:
#    cd backend
#    python main.py
#
# 4. Run your Discord bot
#
# 5. In Discord, use the commands:
#    !deepfake_check https://example.com/video.mp4
#    !backend_status

# ============================================================================
# COMMAND EXAMPLES
# ============================================================================

# !deepfake_check https://example.com/suspicious_video.mp4
#   Analyzes the video at the given URL for deepfake content
#
# !backend_status
#   Shows the current status and available models of the backend

# ============================================================================
# API RESPONSE HANDLING
# ============================================================================

# The backend returns responses like:
# {
#   "is_deepfake": true,
#   "confidence": 0.847,
#   "analysis_time": 1.234,
#   "model_used": "mock"
# }
#
# Error responses:
# {
#   "error": "Invalid URL format",
#   "status_code": 400,
#   "details": null
# }

# ============================================================================
# CUSTOMIZATION OPTIONS
# ============================================================================

# 1. Change model selection:
#    await detector.analyze_url(url, model="deepseek")
#
# 2. Add custom formatting:
#    - Modify the embed creation in deepfake_check()
#    - Add database logging of results
#    - Notify admins of detected deepfakes
#
# 3. Add rate limiting:
#    - Use discord.ext.commands.cooldown decorator
#    - Implement per-user/channel limits
#
# 4. Add file upload support:
#    - Check message attachments
#    - Upload to temporary storage
#    - Generate URL for backend analysis

print("Discord Bot Deepfake Detector Example - Ready to integrate!")
