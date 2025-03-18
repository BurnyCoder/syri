# Syri - AI Voice Assistant

An open-source AI voice assistant that uses:
- AssemblyAI for speech-to-text
- Claude 3.7 Sonnet for AI response generation
- ElevenLabs for text-to-speech

This project enables a fully conversational AI experience similar to Siri, but using powerful AI models and APIs.

## Setup Instructions

### Step 1: Prerequisites

1. **API Keys:**
   - Sign up for a free [AssemblyAI API Key](https://www.assemblyai.com)
   - Sign up for [ElevenLabs](https://www.elevenlabs.io) to get an API key
   - Sign up for [Portkey](https://portkey.ai) to get API keys for Claude 3.7 Sonnet

2. **Install PortAudio** (required for audio recording):
   - Debian/Ubuntu: `apt install portaudio19-dev`
   - MacOS: `brew install portaudio`

3. **For MacOS users only:** Install MPV for audio streaming
   - `brew install mpv`

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

1. Copy the template file to create your own environment file:
   ```bash
   cp .envtemplate .env
   ```

2. Edit the `.env` file and replace the placeholder values with your actual API keys:
   ```
   ASSEMBLYAI_API_KEY=your_actual_assemblyai_key_here
   ELEVENLABS_API_KEY=your_actual_elevenlabs_key_here
   PORTKEY_API_KEY=your_actual_portkey_key_here
   PORTKEY_VIRTUAL_KEY_ANTHROPIC=your_actual_portkey_virtual_key_here
   ```

## Usage

You can run the assistant using either of these methods:

### Method 1: Using the runner script (recommended)

```bash
python run.py
```

This script performs pre-checks to ensure all requirements are met and provides a better user experience.

### Method 2: Direct execution

```bash
python -m src.syri_agent
```

With either method:
1. Press Enter to start recording
2. Speak into your microphone
3. Press Enter again when you've finished speaking
4. The AI will transcribe your speech, process it, and respond both in text (console) and through speech

## How It Works

1. **Audio Recording:** Press Enter to start recording, speak, and press Enter again to stop
2. **Transcription:** Your speech is converted to text using AssemblyAI's transcription API
3. **AI Processing:** The text is sent to Claude 3.7 Sonnet via Portkey for processing
4. **Voice Synthesis:** The AI's response is converted to speech using ElevenLabs
5. **Streaming:** The audio response is streamed back to you

## License

MIT 