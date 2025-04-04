# Syri - AI Voice Assistant

An open-source AI voice assistant that uses:
- OpenAI Whisper for speech-to-text
- Web browser-based agent for AI response generation (using Claude 3.7 Sonnet)
- OpenAI TTS for text-to-speech

This project enables a fully conversational AI experience similar to Siri, but using powerful AI models, a web browser agent, and high-quality audio APIs.

## Setup Instructions

### Step 1: Prerequisites

1. **API Keys:**
   - Sign up for [OpenAI](https://platform.openai.com) to get an API key (used for both STT and TTS)
   - Sign up for [Portkey](https://portkey.ai) to get API keys for Claude 3.7 Sonnet

2. **Install PortAudio** (required for audio recording):
   - Debian/Ubuntu: `apt install portaudio19-dev`
   - MacOS: `brew install portaudio sox`

3. **For MacOS users only:** Install MPV for audio streaming
   - `brew install mpv`

4. **Chrome Browser:**
   - Google Chrome must be installed as the web agent will launch and control Chrome

### Step 2: Install Python Dependencies

```bash
uv sync
```

### Step 3: Configure Environment Variables

1. Copy the template file to create your own environment file:
   ```bash
   cp .envtemplate .env
   ```

2. Edit the `.env` file and replace the placeholder values with your actual API keys:
   ```
   OPENAI_API_KEY=your_actual_openai_key_here
   PORTKEY_API_KEY=your_actual_portkey_key_here
   PORTKEY_VIRTUAL_KEY_ANTHROPIC=your_actual_portkey_virtual_key_here
   ```

   Optional TTS configuration:
   ```
   SYRI_TTS_VOICE=coral     # Options: alloy, echo, fable, onyx, nova, shimmer
   SYRI_TTS_SPEED=1.2       # Speech speed multiplier
   ```

## Usage

You can run the assistant using either of these methods:

### Method 1: Using the runner script (recommended)

```bash
uv run run.py
```

This script performs pre-checks and starts the assistant in an inactive listening state.

1. To start listening, press Enter or run `./scripts/start_listening.sh` (useful for automation)
2. Describe your request
3. Press Enter again or run `./scripts/stop_listening.sh` when done
4. The AI will transcribe your speech, process it through the web agent, and respond both in text (console) and through speech

## Context

This is PoC sketch. Newer version uses OpenAI voice agents and was moved to different repo. 

## How It Works

When you speak to Syri:
1. Your voice is recorded using PyAudio
2. The recording is transcribed to text using OpenAI Whisper
3. The transcribed text is sent to a web agent that runs Chrome browser automation
4. The web agent uses Claude 3.7 Sonnet through Portkey to generate responses
5. The response is converted to speech using OpenAI TTS

## License

MIT 