#!/usr/bin/env python3
"""
StudySage Telegram Bot - AI-powered study assistant using Google Gemini
"""

import os
import logging
import asyncio
import tempfile
from typing import Final
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from google import genai

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN: Final = os.environ.get('TELEGRAM_BOT_TOKEN')
GEMINI_API_KEY: Final = os.environ.get('GEMINI_API_KEY')

# Initialize Gemini AI client
if GEMINI_API_KEY:
    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
    genai_client = genai.Client()
else:
    logger.error("GEMINI_API_KEY not found in environment variables")
    genai_client = None

class StudySageBot:
    def __init__(self):
        self.model = "gemini-2.0-flash-001"
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        welcome_message = """
🤖 Welcome to StudySage! 📚

I'm your AI-powered study assistant, ready to help you with:
• Homework questions and problem solving
• Concept explanations
• Study tips and strategies
• Research assistance
• Practice problems
• 📸 Image analysis (diagrams, handwritten notes, math problems)
• 🎥 Video content analysis and transcription
• And much more!

Just send me any question, image, or video, and I'll provide detailed, helpful responses using advanced AI.

Type /help to see available commands.
        """
        await update.message.reply_text(welcome_message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a help message when the command /help is issued."""
        help_text = """
📋 StudySage Commands:

/start - Start the bot and see welcome message
/help - Show this help message
/clear - Clear conversation context (fresh start)

💡 How to use:
I can help you in multiple ways:

📝 Text Questions:
• Academic subjects (math, science, history, etc.)
• Homework assistance and explanations
• Study strategies and research topics
• Creative writing help

📸 Image Analysis:
• Math problems and equations
• Diagrams and charts
• Handwritten notes
• Scientific illustrations
• Historical documents

🎥 Video Analysis:
• Educational videos
• Lecture recordings
• Lab demonstrations
• Video transcription

Example: Send "Explain photosynthosis" or upload a photo of a math problem!
        """
        await update.message.reply_text(help_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear conversation context."""
        await update.message.reply_text("🔄 Conversation context cleared! Starting fresh.")
        
    async def download_file(self, file_id: str, context: ContextTypes.DEFAULT_TYPE) -> str:
        """Download a file from Telegram and return the local file path."""
        try:
            # Get file from Telegram
            telegram_file = await context.bot.get_file(file_id)
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tmp')
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Download file
            await telegram_file.download_to_drive(temp_file_path)
            
            logger.info(f"Downloaded file to {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            raise
            
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo messages and analyze them with AI."""
        if not genai_client:
            await update.message.reply_text(
                "❌ AI service is not available. Please check the configuration."
            )
            return

        user_name = update.effective_user.first_name or "Student"
        logger.info(f"User {user_name} sent a photo")
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        try:
            # Get the largest photo size
            photo = update.message.photo[-1]
            
            # Download the photo
            photo_path = await self.download_file(photo.file_id, context)
            
            # Get caption if provided
            caption = update.message.caption or "Analyze this image"
            
            # Upload to Gemini
            image_file = genai_client.files.upload(file=photo_path)
            
            # Create enhanced prompt for image analysis
            enhanced_prompt = f"""
You are StudySage, an intelligent study assistant. A student named {user_name} has shared an image with you.

Student's message: "{caption}"

Please analyze this image and provide educational assistance. Follow these guidelines:
- If it's a math problem, guide them through the solution step-by-step
- If it's a diagram, explain what it shows and its educational significance
- If it's handwritten notes, help clarify or expand on the content
- If it's a scientific illustration, explain the concepts shown
- Be encouraging and educational in your response
- Use appropriate emojis to make the response engaging
- If you can't clearly see the content, ask for clarification

Please analyze the image and provide helpful educational assistance.
            """
            
            # Generate response using Gemini vision
            response = genai_client.models.generate_content(
                model=self.model,
                contents=[enhanced_prompt, image_file]
            )
            
            if response and response.text:
                # Split long messages to avoid Telegram's character limit
                ai_response = response.text.strip()
                if len(ai_response) > 4000:
                    chunks = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(ai_response)
                    
                logger.info(f"AI image analysis sent to {user_name}")
            else:
                await update.message.reply_text(
                    "🤔 I'm having trouble analyzing this image right now. Please try again in a moment."
                )
                
            # Clean up temporary file
            try:
                os.unlink(photo_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error processing photo: {e}")
            await update.message.reply_text(
                "⚠️ Sorry, I encountered an error while analyzing your image. Please try again."
            )
            
    async def handle_video(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle video messages and analyze them with AI."""
        if not genai_client:
            await update.message.reply_text(
                "❌ AI service is not available. Please check the configuration."
            )
            return

        user_name = update.effective_user.first_name or "Student"
        logger.info(f"User {user_name} sent a video")
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        try:
            # Get video file
            video = update.message.video
            
            # Check video size (Gemini has limits)
            if video.file_size > 20 * 1024 * 1024:  # 20MB limit
                await update.message.reply_text(
                    "📹 Your video is quite large. For better processing, please try uploading a smaller video (under 20MB) or a shorter clip."
                )
                return
            
            # Download the video
            video_path = await self.download_file(video.file_id, context)
            
            # Get caption if provided
            caption = update.message.caption or "Analyze this video"
            
            # Upload to Gemini
            video_file = genai_client.files.upload(file=video_path)
            
            # Create enhanced prompt for video analysis
            enhanced_prompt = f"""
You are StudySage, an intelligent study assistant. A student named {user_name} has shared a video with you.

Student's message: "{caption}"

Please analyze this video and provide educational assistance. Follow these guidelines:
- If it's an educational video, summarize the key concepts
- If it contains audio, provide transcription when helpful
- If it shows a demonstration or experiment, explain what's happening
- If it's a lecture recording, highlight the main points
- Provide timestamps for important moments when relevant
- Be encouraging and educational in your response
- Use appropriate emojis to make the response engaging
- If the video is unclear or too long, ask for clarification

Please analyze the video content and provide helpful educational assistance.
            """
            
            # Generate response using Gemini multimodal
            response = genai_client.models.generate_content(
                model=self.model,
                contents=[enhanced_prompt, video_file]
            )
            
            if response and response.text:
                # Split long messages to avoid Telegram's character limit
                ai_response = response.text.strip()
                if len(ai_response) > 4000:
                    chunks = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(ai_response)
                    
                logger.info(f"AI video analysis sent to {user_name}")
            else:
                await update.message.reply_text(
                    "🤔 I'm having trouble analyzing this video right now. Please try again in a moment."
                )
                
            # Clean up temporary file
            try:
                os.unlink(video_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error processing video: {e}")
            await update.message.reply_text(
                "⚠️ Sorry, I encountered an error while analyzing your video. Please try again."
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages and generate AI responses."""
        if not genai_client:
            await update.message.reply_text(
                "❌ AI service is not available. Please check the configuration."
            )
            return

        user_message = update.message.text
        user_name = update.effective_user.first_name or "Student"
        
        # Log the incoming message
        logger.info(f"User {user_name}: {user_message}")
        
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        try:
            # Create enhanced prompt for study assistance
            enhanced_prompt = f"""
You are StudySage, an intelligent and helpful study assistant. A student named {user_name} has asked you: "{user_message}"

Please provide a clear, educational, and helpful response. Follow these guidelines:
- Be encouraging and supportive
- Explain concepts clearly and step-by-step when needed
- Provide examples where helpful
- If it's a homework question, guide them through the thinking process rather than just giving the answer
- Use appropriate emojis to make the response engaging
- Keep responses concise but comprehensive
- If the question is unclear, ask for clarification

Student's question: {user_message}
            """
            
            # Generate response using Gemini
            response = genai_client.models.generate_content(
                model=self.model,
                contents=enhanced_prompt
            )
            
            if response and response.text:
                # Split long messages to avoid Telegram's 4096 character limit
                ai_response = response.text.strip()
                if len(ai_response) > 4000:
                    # Split into chunks
                    chunks = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
                    for chunk in chunks:
                        await update.message.reply_text(chunk)
                else:
                    await update.message.reply_text(ai_response)
                    
                logger.info(f"AI response sent to {user_name}")
            else:
                await update.message.reply_text(
                    "🤔 I'm having trouble generating a response right now. Please try again in a moment."
                )
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            await update.message.reply_text(
                "⚠️ Sorry, I encountered an error while processing your request. Please try again."
            )

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log errors and notify the user."""
        logger.error(f"Update {update} caused error {context.error}")
        
        if hasattr(update, 'effective_message') and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An unexpected error occurred. Please try again later."
            )

def main():
    """Start the bot."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return
        
    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not found in environment variables")
        return
    
    # Create bot instance
    bot = StudySageBot()
    
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("clear", bot.clear_command))
    
    # Media handlers
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO, bot.handle_video))
    
    # Text message handler (keep this last to avoid conflicts)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))
    
    # Add error handler
    application.add_error_handler(bot.error_handler)
    
    # Start the bot
    logger.info("StudySage bot is starting...")
    print("🚀 StudySage bot is running!")
    print("Press Ctrl+C to stop the bot")
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()