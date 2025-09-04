#!/usr/bin/env python3
"""
StudySage Telegram Bot - AI-powered study assistant using Google Gemini
"""

import os
import logging
import asyncio
import tempfile
import json
import datetime
import random
from typing import Final, Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler
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
        # User data storage (in production, use a proper database)
        self.user_data: Dict[int, Dict] = {}
        
    def get_user_data(self, user_id: int) -> Dict:
        """Get or create user data."""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                'study_streak': 0,
                'total_questions': 0,
                'correct_answers': 0,
                'subjects_studied': set(),
                'last_activity': None,
                'level': 1,
                'xp': 0,
                'preferences': {
                    'difficulty': 'medium',
                    'reminder_time': None,
                    'favorite_subjects': []
                }
            }
        return self.user_data[user_id]
        
    def update_user_stats(self, user_id: int, subject: str = None, correct: bool = None):
        """Update user statistics and XP."""
        data = self.get_user_data(user_id)
        data['last_activity'] = datetime.datetime.now().isoformat()
        
        if subject:
            data['subjects_studied'].add(subject)
            
        if correct is not None:
            data['total_questions'] += 1
            if correct:
                data['correct_answers'] += 1
                data['xp'] += 10
            else:
                data['xp'] += 2
                
        # Level up system
        new_level = min(10, data['xp'] // 100 + 1)
        if new_level > data['level']:
            data['level'] = new_level
            return True  # Level up!
        return False
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send a message when the command /start is issued."""
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        user_name = update.effective_user.first_name or "Student"
        
        welcome_message = f"""
🎓 **Welcome back, {user_name}!** 🤖✨

🔥 **StudySage Pro** - Your Ultimate AI Study Companion

🏆 **Your Progress:**
• Level {user_data['level']} 🎆 ({user_data['xp']} XP)
• Study Streak: {user_data['study_streak']} days 🔥
• Questions Answered: {user_data['total_questions']}
• Accuracy: {(user_data['correct_answers']/max(1,user_data['total_questions'])*100):.1f}%

🚀 **Choose what you'd like to do:**
        """
        
        # Create interactive keyboard
        keyboard = [
            [
                InlineKeyboardButton("📝 Ask Question", callback_data="ask_question"),
                InlineKeyboardButton("🧠 Generate Quiz", callback_data="generate_quiz")
            ],
            [
                InlineKeyboardButton("📊 My Progress", callback_data="show_progress"),
                InlineKeyboardButton("🏆 Achievements", callback_data="achievements")
            ],
            [
                InlineKeyboardButton("📋 Flashcards", callback_data="flashcards"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton("📚 Study Subjects", callback_data="subjects"),
                InlineKeyboardButton("📈 Analytics", callback_data="analytics")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_message, reply_markup=reply_markup, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send advanced help with interactive buttons."""
        help_text = """
📢 **StudySage Pro Help** 💡

📝 **Commands:**
• `/start` - Main dashboard
• `/quiz` - Generate instant quiz
• `/progress` - View your stats
• `/remind` - Set study reminders
• `/subjects` - Manage subjects
• `/help` - This help menu

📱 **What I can analyze:**
• 📝 Text questions (any subject)
• 📸 Photos (math, diagrams, notes)
• 🎥 Videos (lectures, demos)
• 🎙️ Voice messages (transcription)

🎮 **Gamification Features:**
• XP points for every question
• 10 levels to unlock
• Study streak tracking
• Achievement badges
• Progress analytics

🚀 **Quick Tips:**
• Ask specific questions for better answers
• Upload images for visual problem solving
• Use voice messages for hands-free help
• Take quizzes to test your knowledge

💬 Need specific help with any feature?
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🚀 Try a Quiz Now", callback_data="generate_quiz"),
                InlineKeyboardButton("📊 My Dashboard", callback_data="dashboard")
            ],
            [
                InlineKeyboardButton("📱 Feature Guide", callback_data="feature_guide"),
                InlineKeyboardButton("🎯 Practice Mode", callback_data="practice_mode")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode='Markdown')

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Clear conversation context with confirmation."""
        keyboard = [
            [
                InlineKeyboardButton("✅ Yes, Clear", callback_data="confirm_clear"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_clear")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔄 **Clear conversation context?**\n\nThis will reset our current conversation but keep your progress data.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
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
            
    async def handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle voice messages and transcribe them."""
        if not genai_client:
            await update.message.reply_text(
                "❌ AI service is not available. Please check the configuration."
            )
            return

        user_name = update.effective_user.first_name or "Student"
        logger.info(f"User {user_name} sent a voice message")
        
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action='typing')
        
        try:
            # Download voice message
            voice_path = await self.download_file(update.message.voice.file_id, context)
            
            # Upload to Gemini for transcription
            audio_file = genai_client.files.upload(file=voice_path)
            
            # Enhanced prompt for voice transcription
            enhanced_prompt = f"""
You are StudySage, an intelligent study assistant. A student named {user_name} has sent you a voice message.

Please:
1. Transcribe the audio accurately
2. Understand the educational question or topic
3. Provide a helpful response to their study question
4. If it's a complex topic, break it down step-by-step
5. Be encouraging and educational

Transcribe and respond to this voice message:
            """
            
            # Generate response
            response = genai_client.models.generate_content(
                model=self.model,
                contents=[enhanced_prompt, audio_file]
            )
            
            if response and response.text:
                # Add voice icon and format response
                ai_response = f"🎙️ **Voice Message Processed:**\n\n{response.text.strip()}"
                
                if len(ai_response) > 4000:
                    chunks = [ai_response[i:i+4000] for i in range(0, len(ai_response), 4000)]
                    for chunk in chunks:
                        await update.message.reply_text(chunk, parse_mode='Markdown')
                else:
                    await update.message.reply_text(ai_response, parse_mode='Markdown')
                    
                # Update user stats
                self.update_user_stats(update.effective_user.id)
                logger.info(f"AI voice response sent to {user_name}")
            else:
                await update.message.reply_text(
                    "🤔 I'm having trouble processing your voice message right now. Please try again."
                )
                
            # Clean up
            try:
                os.unlink(voice_path)
            except:
                pass
                
        except Exception as e:
            logger.error(f"Error processing voice: {e}")
            await update.message.reply_text(
                "⚠️ Sorry, I encountered an error while processing your voice message. Please try again."
            )
            
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all callback queries from inline keyboards."""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = self.get_user_data(user_id)
        
        if query.data == "ask_question":
            await query.edit_message_text(
                "📝 **Ask me anything!**\n\n🚀 Send me:\n• Text questions\n• 📸 Photos of problems\n• 🎥 Educational videos\n• 🎙️ Voice messages\n\nI'll analyze and help you understand!",
                parse_mode='Markdown'
            )
            
        elif query.data == "generate_quiz":
            await self.generate_quiz(query, user_data)
            
        elif query.data == "show_progress":
            await self.show_progress(query, user_data)
            
        elif query.data == "achievements":
            await self.show_achievements(query, user_data)
            
        elif query.data == "flashcards":
            await self.show_flashcards(query, user_data)
            
        elif query.data == "settings":
            await self.show_settings(query, user_data)
            
        elif query.data == "subjects":
            await self.show_subjects(query, user_data)
            
        elif query.data == "analytics":
            await self.show_analytics(query, user_data)
            
        elif query.data == "dashboard":
            # Redirect to start command functionality
            await self.show_dashboard(query, user_data)
            
        elif query.data == "confirm_clear":
            await query.edit_message_text("🔄 **Context cleared!** Starting fresh. Use /start to return to the main menu.")
            
        elif query.data == "cancel_clear":
            await query.edit_message_text("❌ **Cancelled.** Your conversation context remains intact.")
            
        elif query.data.startswith("quiz_"):
            await self.handle_quiz_answer(query, user_data)
            
        elif query.data.startswith("difficulty_"):
            difficulty = query.data.split("_")[1]
            user_data['preferences']['difficulty'] = difficulty
            await query.edit_message_text(f"✅ **Difficulty set to {difficulty.title()}!**\n\nThis will affect future quizzes and recommendations.")
            
    async def generate_quiz(self, query, user_data):
        """Generate an interactive quiz."""
        subjects = ['Math', 'Science', 'History', 'Literature', 'Geography', 'Physics', 'Chemistry', 'Biology']
        
        keyboard = []
        for i in range(0, len(subjects), 2):
            row = []
            row.append(InlineKeyboardButton(f"📚 {subjects[i]}", callback_data=f"quiz_subject_{subjects[i].lower()}"))
            if i + 1 < len(subjects):
                row.append(InlineKeyboardButton(f"📚 {subjects[i+1]}", callback_data=f"quiz_subject_{subjects[i+1].lower()}"))
            keyboard.append(row)
            
        keyboard.append([InlineKeyboardButton("🎲 Random Topic", callback_data="quiz_subject_random")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🧠 **Quiz Generator** 🎯\n\n🏆 Level {user_data['level']} Student\n\nChoose a subject for your quiz:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def show_progress(self, query, user_data):
        """Show user progress and statistics."""
        accuracy = (user_data['correct_answers'] / max(1, user_data['total_questions']) * 100)
        xp_to_next = (user_data['level'] * 100) - user_data['xp']
        
        progress_text = f"""
📈 **Your Study Progress** 🏆

🎆 **Level:** {user_data['level']}/10
⚡ **XP:** {user_data['xp']} ({xp_to_next} to next level)
🔥 **Study Streak:** {user_data['study_streak']} days

📉 **Quiz Statistics:**
• Questions Answered: {user_data['total_questions']}
• Correct Answers: {user_data['correct_answers']}
• Accuracy Rate: {accuracy:.1f}%

📚 **Subjects Studied:** {len(user_data['subjects_studied'])}
{', '.join(list(user_data['subjects_studied'])[:5]) if user_data['subjects_studied'] else 'None yet'}

📅 **Last Activity:** {user_data['last_activity'][:10] if user_data['last_activity'] else 'Never'}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📈 Detailed Analytics", callback_data="analytics"),
                InlineKeyboardButton("🏆 Achievements", callback_data="achievements")
            ],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="dashboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(progress_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def show_achievements(self, query, user_data):
        """Show user achievements and badges."""
        achievements = []
        
        # Check various achievements
        if user_data['total_questions'] >= 10:
            achievements.append("🎆 Curious Learner (10+ questions)")
        if user_data['total_questions'] >= 50:
            achievements.append("🏆 Quiz Master (50+ questions)")
        if user_data['study_streak'] >= 3:
            achievements.append("🔥 Study Streak (3+ days)")
        if user_data['level'] >= 3:
            achievements.append("⭐ Rising Star (Level 3+)")
        if user_data['level'] >= 5:
            achievements.append("🌟 Study Expert (Level 5+)")
        if len(user_data['subjects_studied']) >= 3:
            achievements.append("📚 Multi-Subject Scholar")
            
        achievement_text = f"""
🏆 **Your Achievements** 🎆

✨ **Unlocked Badges:**
{chr(10).join(achievements) if achievements else '❌ No achievements yet - keep studying!'}

🚯 **Upcoming Achievements:**
• 💯 Perfect Score (100% accuracy in 5 quizzes)
• 🚀 Knowledge Seeker (Level 10)
• 🏅 Subject Expert (Master 5 subjects)
• 🔥 Fire Streak (7-day study streak)

💪 Keep studying to unlock more badges!
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Progress", callback_data="show_progress")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(achievement_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def show_flashcards(self, query, user_data):
        """Show flashcard options."""
        flashcard_text = """
📋 **Flashcard Generator** 🧠

🎯 Create instant flashcards from any content!

🚀 **How to use:**
1. Send me any text, image, or topic
2. Add the word "flashcard" to your message
3. I'll generate study cards for you!

💡 **Example:**
"Create flashcards about photosynthesis"
"Make flashcards from this image"
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Create from Text", callback_data="flashcard_text"),
                InlineKeyboardButton("📸 Create from Image", callback_data="flashcard_image")
            ],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="dashboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(flashcard_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def show_settings(self, query, user_data):
        """Show user settings and preferences."""
        current_difficulty = user_data['preferences']['difficulty'].title()
        
        settings_text = f"""
⚙️ **StudySage Settings** 📁

🎯 **Current Preferences:**
• Difficulty: {current_difficulty}
• Reminder: {'Set' if user_data['preferences']['reminder_time'] else 'Not set'}
• Favorite Subjects: {len(user_data['preferences']['favorite_subjects'])}

🔧 **Customize your experience:**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 Set Difficulty", callback_data="set_difficulty"),
                InlineKeyboardButton("⏰ Study Reminders", callback_data="set_reminders")
            ],
            [
                InlineKeyboardButton("📚 Favorite Subjects", callback_data="set_subjects"),
                InlineKeyboardButton("🎨 Personalization", callback_data="personalize")
            ],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="dashboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def show_subjects(self, query, user_data):
        """Show subject management."""
        studied_subjects = list(user_data['subjects_studied'])[:10]  # Show first 10
        
        subjects_text = f"""
📚 **Subject Management** 🎨

🏆 **Subjects You've Studied:**
{chr(10).join([f'• {subject}' for subject in studied_subjects]) if studied_subjects else '❌ No subjects studied yet'}

🚀 **Available Categories:**
• Mathematics & Algebra
• Science & Physics
• Literature & Languages
• History & Geography
• Computer Science
• Arts & Philosophy

💡 Start asking questions to track your subjects!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🧠 Generate Subject Quiz", callback_data="generate_quiz"),
                InlineKeyboardButton("📈 Subject Analytics", callback_data="analytics")
            ],
            [InlineKeyboardButton("🔙 Back to Main", callback_data="dashboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(subjects_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def show_analytics(self, query, user_data):
        """Show detailed analytics."""
        total_days = max(1, (datetime.datetime.now() - datetime.datetime.fromisoformat(user_data['last_activity'])).days) if user_data['last_activity'] else 1
        avg_questions = user_data['total_questions'] / total_days
        
        analytics_text = f"""
📈 **Detailed Analytics** 🔍

📅 **Time-based Stats:**
• Average questions/day: {avg_questions:.1f}
• Total study sessions: {max(1, user_data['total_questions'] // 5)}
• Peak performance: Level {user_data['level']}

🏆 **Performance Metrics:**
• Success rate: {(user_data['correct_answers']/max(1,user_data['total_questions'])*100):.1f}%
• XP efficiency: {user_data['xp']/(max(1,user_data['total_questions'])):.1f} XP/question
• Subject diversity: {len(user_data['subjects_studied'])}

📉 **Growth Tracking:**
• Level progression: {((user_data['level']-1)/9*100):.1f}% complete
• Knowledge areas: {len(user_data['subjects_studied'])}/20 explored

🚀 **Recommendations:**
• {'Try more challenging questions!' if user_data['level'] < 5 else 'You are doing great - keep it up!'}
• {'Explore new subjects!' if len(user_data['subjects_studied']) < 3 else 'Great subject diversity!'}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📧 Export Data", callback_data="export_data"),
                InlineKeyboardButton("🔄 Reset Stats", callback_data="reset_stats")
            ],
            [InlineKeyboardButton("🔙 Back to Progress", callback_data="show_progress")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(analytics_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def handle_quiz_answer(self, query, user_data):
        """Handle quiz answers and generate questions."""
        if query.data.startswith("quiz_subject_"):
            subject = query.data.replace("quiz_subject_", "").replace("_", " ").title()
            
            if subject == "Random":
                subjects = ['Math', 'Science', 'History', 'Literature', 'Geography', 'Physics']
                subject = random.choice(subjects)
                
            # Generate quiz question using AI
            await self.generate_quiz_question(query, subject, user_data)
            
    async def generate_quiz_question(self, query, subject, user_data):
        """Generate an AI-powered quiz question."""
        difficulty = user_data['preferences']['difficulty']
        level = user_data['level']
        
        quiz_prompt = f"""
Generate a {difficulty} difficulty {subject} quiz question suitable for a Level {level} student.

Format your response EXACTLY like this:
**Question:** [Your question here]

**A)** [Option A]
**B)** [Option B] 
**C)** [Option C]
**D)** [Option D]

**Correct Answer:** [A, B, C, or D]
**Explanation:** [Brief explanation why this is correct]

Make it educational and engaging!
        """
        
        try:
            response = genai_client.models.generate_content(
                model=self.model,
                contents=quiz_prompt
            )
            
            if response and response.text:
                quiz_text = response.text.strip()
                
                # Create answer buttons
                keyboard = [
                    [
                        InlineKeyboardButton("🅰️ A", callback_data="quiz_answer_A"),
                        InlineKeyboardButton("🅱️ B", callback_data="quiz_answer_B")
                    ],
                    [
                        InlineKeyboardButton("🄲️ C", callback_data="quiz_answer_C"),
                        InlineKeyboardButton("🄳️ D", callback_data="quiz_answer_D")
                    ],
                    [
                        InlineKeyboardButton("🔄 New Question", callback_data="generate_quiz"),
                        InlineKeyboardButton("🔙 Main Menu", callback_data="dashboard")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    f"🧠 **{subject} Quiz** 🏆\n\n{quiz_text}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                # Store quiz data for answer checking
                context_data = query.message.chat.id
                
            else:
                await query.edit_message_text("⚠️ Failed to generate quiz. Please try again!")
                
        except Exception as e:
            logger.error(f"Quiz generation error: {e}")
            await query.edit_message_text("⚠️ Quiz generation failed. Please try again later.")
            
    async def quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Quick quiz command."""
        user_data = self.get_user_data(update.effective_user.id)
        
        keyboard = [
            [
                InlineKeyboardButton("🧠 Start Quiz", callback_data="generate_quiz"),
                InlineKeyboardButton("📈 My Progress", callback_data="show_progress")
            ],
            [
                InlineKeyboardButton("🎯 Practice Mode", callback_data="practice_mode"),
                InlineKeyboardButton("📚 Study Subjects", callback_data="subjects")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🧠 **Quick Quiz Access** 🎯\n\n🏆 Level {user_data['level']} Student\n\nReady to test your knowledge?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    async def progress_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Quick progress command."""
        user_data = self.get_user_data(update.effective_user.id)
        accuracy = (user_data['correct_answers'] / max(1, user_data['total_questions']) * 100)
        
        progress_text = f"""
📈 **Quick Progress Check** 🏆

🎆 Level: {user_data['level']}/10 (⚡ {user_data['xp']} XP)
🔥 Study Streak: {user_data['study_streak']} days
🎯 Accuracy: {accuracy:.1f}% ({user_data['correct_answers']}/{user_data['total_questions']})
📚 Subjects: {len(user_data['subjects_studied'])}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📈 Detailed Stats", callback_data="analytics"),
                InlineKeyboardButton("🏆 Achievements", callback_data="achievements")
            ],
            [InlineKeyboardButton("🚀 Dashboard", callback_data="dashboard")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(progress_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def subjects_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Quick subjects command."""
        user_data = self.get_user_data(update.effective_user.id)
        studied = list(user_data['subjects_studied'])[:5]
        
        subjects_text = f"""
📚 **Subject Quick Access** 🎨

🏆 Your studied subjects ({len(user_data['subjects_studied'])}):
{chr(10).join([f'• {subject}' for subject in studied]) if studied else '❌ Start studying to track subjects!'}

🚀 What would you like to do?
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🧠 Subject Quiz", callback_data="generate_quiz"),
                InlineKeyboardButton("📋 Subject Analytics", callback_data="analytics")
            ],
            [
                InlineKeyboardButton("📝 Ask Question", callback_data="ask_question"),
                InlineKeyboardButton("🚀 Dashboard", callback_data="dashboard")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(subjects_text, reply_markup=reply_markup, parse_mode='Markdown')
        
    async def show_dashboard(self, query, user_data):
        """Show main dashboard."""
        user_name = query.from_user.first_name or "Student"
        
        dashboard_text = f"""
🎓 **StudySage Pro Dashboard** 🤖✨

Welcome back, {user_name}! 🚀

🏆 **Your Progress:**
• Level {user_data['level']} 🎆 ({user_data['xp']} XP)
• Study Streak: {user_data['study_streak']} days 🔥
• Questions Answered: {user_data['total_questions']}
• Accuracy: {(user_data['correct_answers']/max(1,user_data['total_questions'])*100):.1f}%

🚀 **What would you like to do?**
        """
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Ask Question", callback_data="ask_question"),
                InlineKeyboardButton("🧠 Generate Quiz", callback_data="generate_quiz")
            ],
            [
                InlineKeyboardButton("📊 My Progress", callback_data="show_progress"),
                InlineKeyboardButton("🏆 Achievements", callback_data="achievements")
            ],
            [
                InlineKeyboardButton("📋 Flashcards", callback_data="flashcards"),
                InlineKeyboardButton("⚙️ Settings", callback_data="settings")
            ],
            [
                InlineKeyboardButton("📚 Study Subjects", callback_data="subjects"),
                InlineKeyboardButton("📈 Analytics", callback_data="analytics")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(dashboard_text, reply_markup=reply_markup, parse_mode='Markdown')

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
    
    # Command handlers
    application.add_handler(CommandHandler("start", bot.start_command))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("clear", bot.clear_command))
    application.add_handler(CommandHandler("quiz", bot.quiz_command))
    application.add_handler(CommandHandler("progress", bot.progress_command))
    application.add_handler(CommandHandler("subjects", bot.subjects_command))
    
    # Callback query handler for interactive buttons
    application.add_handler(CallbackQueryHandler(bot.handle_callback))
    
    # Media handlers
    application.add_handler(MessageHandler(filters.PHOTO, bot.handle_photo))
    application.add_handler(MessageHandler(filters.VIDEO, bot.handle_video))
    application.add_handler(MessageHandler(filters.VOICE, bot.handle_voice))
    
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