# Syri - AI Voice Assistant

An open-source AI voice assistant that uses:
- AssemblyAI for real-time speech-to-text
- DeepSeek R1 for AI response generation
- ElevenLabs for text-to-speech

This project enables a fully conversational AI experience similar to Siri, but using open models and APIs.

## Setup Instructions

### Step 1: Prerequisites

1. **API Keys:**
   - Sign up for a free [AssemblyAI API Key](https://www.assemblyai.com)
   - Sign up for [ElevenLabs](https://www.elevenlabs.io) to get an API key

2. **Install Ollama:**
   - Download from [Ollama's website](https://ollama.com)

3. **Install PortAudio** (required for real-time transcription):
   - Debian/Ubuntu: `apt install portaudio19-dev`
   - MacOS: `brew install portaudio`

4. **For MacOS users only:** Install MPV for audio streaming
   - `brew install mpv`

### Step 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Download the AI Model

```bash
ollama pull deepseek-r1:7b
```

### Step 4: Configure Environment Variables

1. Copy the template file to create your own environment file:
   ```bash
   cp .envtemplate .env
   ```

2. Edit the `.env` file and replace the placeholder values with your actual API keys:
   ```
   ASSEMBLYAI_API_KEY=your_actual_assemblyai_key_here
   ELEVENLABS_API_KEY=your_actual_elevenlabs_key_here
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
python syri_agent.py
```

With either method, speak into your microphone when prompted, and the AI will respond both in text (console) and through speech.

## How It Works

1. **Real-Time Transcription:** Your speech is captured and converted to text using AssemblyAI
2. **AI Processing:** The text is sent to DeepSeek R1 via Ollama for processing
3. **Voice Synthesis:** The AI's response is converted to speech using ElevenLabs
4. **Streaming:** The audio response is streamed back to you in real-time

## License

MIT 