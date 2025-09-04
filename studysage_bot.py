#!/usr/bin/env python3
"""
StudySage Telegram Bot - AI-powered study assistant using Google Gemini
"""

import os
import logging
import asyncio
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
• Homework questions
• Concept explanations
• Study tips and strategies
• Research assistance
• Practice problems
• And much more!

Just send me any question or topic you'd like to explore, and I'll provide detailed, helpful responses using advanced AI.

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
Simply send me any question or message! I can help with:
• Academic subjects (math, science, history, etc.)
• Homework assistance
• Concept explanations
• Study strategies
• Research topics
• Creative writing
• And much more!

Example: "Explain photosynthesis" or "Help me solve this math problem: 2x + 5 = 15"
        """
        await update.message.reply_text(help_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear conversation context."""
        await update.message.reply_text("🔄 Conversation context cleared! Starting fresh.")

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