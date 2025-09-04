# StudySage Telegram Bot

## Overview

StudySage is an AI-powered Telegram bot designed to serve as a comprehensive study assistant. The bot leverages Google's Gemini AI model to provide educational support including homework help, concept explanations, study strategies, research assistance, and practice problems. Built with Python using the python-telegram-bot library, it offers students an accessible and intelligent learning companion through the familiar Telegram interface.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Framework
- **Python-based Implementation**: Uses the `python-telegram-bot` library for handling Telegram API interactions
- **Asynchronous Design**: Built with async/await patterns for efficient handling of concurrent user requests
- **Command and Message Handling**: Supports both command-based interactions (/start) and natural language message processing

### AI Integration
- **Google Gemini Integration**: Utilizes Google's Gemini 2.0 Flash model for AI-powered responses
- **Model Selection**: Configured to use "gemini-2.0-flash-001" for optimal balance of speed and capability
- **Client Initialization**: Implements proper error handling for API key validation and client setup

### Configuration Management
- **Environment Variable Configuration**: Uses environment variables for sensitive data (bot token, API keys)
- **Logging System**: Comprehensive logging setup with timestamp, logger name, and level information
- **Error Handling**: Graceful handling of missing API keys and configuration issues

### Application Structure
- **Class-based Architecture**: StudySageBot class encapsulates bot functionality for better organization
- **Handler Registration**: Structured approach to registering command and message handlers
- **Modular Design**: Clean separation between bot initialization, command handling, and AI processing

## External Dependencies

### Telegram Bot API
- **python-telegram-bot**: Primary library for Telegram bot functionality
- **Integration Purpose**: Handles all Telegram-specific operations including message receiving, sending, and user interaction management

### Google Gemini AI
- **Google GenAI Library**: Provides access to Google's Gemini AI models
- **Model Used**: Gemini 2.0 Flash (gemini-2.0-flash-001)
- **Purpose**: Powers the intelligent responses and educational assistance capabilities

### Environment Configuration
- **Required Environment Variables**:
  - `TELEGRAM_BOT_TOKEN`: Authentication token for Telegram Bot API
  - `GEMINI_API_KEY`: API key for Google Gemini AI service

### Python Standard Libraries
- **asyncio**: Asynchronous programming support
- **logging**: Application logging and debugging
- **os**: Environment variable access and system operations
- **typing**: Type hints for better code documentation and IDE support