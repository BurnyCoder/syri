import assemblyai as aai
import elevenlabs
from elevenlabs import stream, set_api_key
import os
from dotenv import load_dotenv
from src.portkey import claude37sonnet

# Load environment variables from .env file
load_dotenv()


class AIVoiceAgent:
    def __init__(self):
        # Get API keys from environment variables
        assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        portkey_virtual_key = os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        
        # Check if API keys are available
        if not assemblyai_api_key:
            raise ValueError("AssemblyAI API key not found. Please set ASSEMBLYAI_API_KEY in your .env file")
        if not elevenlabs_api_key:
            raise ValueError("ElevenLabs API key not found. Please set ELEVENLABS_API_KEY in your .env file")
        if not portkey_api_key:
            raise ValueError("Portkey API key not found. Please set PORTKEY_API_KEY in your .env file")
        if not portkey_virtual_key:
            raise ValueError("Portkey Virtual Key not found. Please set PORTKEY_VIRTUAL_KEY_ANTHROPIC in your .env file")
            
        aai.settings.api_key = assemblyai_api_key
        # Set ElevenLabs API key
        set_api_key(elevenlabs_api_key)
        # No need to initialize a client with newer versions of elevenlabs
        
        self.transcriber = None

        self.full_transcript = [
            {"role": "system", "content": "You are a helpful AI assistant called Syri. Provide concise, friendly responses under 300 characters."},
        ]

    def start_transcription(self):
        print(f"\nReal-time transcription: ", end="\r\n")
        self.transcriber = aai.RealtimeTranscriber(
            sample_rate=16_000,
            on_data=self.on_data,
            on_error=self.on_error,
            on_open=self.on_open,
            on_close=self.on_close,
        )
        self.transcriber.connect()
        microphone_stream = aai.extras.MicrophoneStream(sample_rate=16_000)
        self.transcriber.stream(microphone_stream)

    def stop_transcription(self):
        if self.transcriber:
            self.transcriber.close()
            self.transcriber = None

    def on_open(self, session_opened: aai.RealtimeSessionOpened):
        # print("Session ID:", session_opened.session_id)
        return
    
    def on_data(self, transcript: aai.RealtimeTranscript):
        if not transcript.text:
            return

        if isinstance(transcript, aai.RealtimeFinalTranscript):
            print(transcript.text)
            self.generate_ai_response(transcript)
        else:
            print(transcript.text, end="\r")

    def on_error(self, error: aai.RealtimeError):
        # print("An error occured:", error)
        return

    def on_close(self):
        # print("Closing Session")
        return    
    
    def generate_ai_response(self, transcript):
        self.stop_transcription()

        self.full_transcript.append({"role": "user", "content": transcript.text})
        print(f"\nUser: {transcript.text}", end="\r\n")

        print("Claude 3.7 Sonnet:", end="\r\n")
        
        # Get response from Claude 3.7 Sonnet using the full conversation history
        response_text = claude37sonnet(self.full_transcript)
        
        # Break the response into sentences for streaming audio
        sentences = []
        temp = ""
        for char in response_text:
            temp += char
            if char in ['.', '!', '?'] and len(temp.strip()) > 0:
                sentences.append(temp)
                temp = ""
        
        if temp:  # Add any remaining text
            sentences.append(temp)
        
        full_text = ""
        # Process each sentence
        for sentence in sentences:
            audio_stream = elevenlabs.generate(
                text=sentence,
                model="eleven_turbo_v2",
                stream=True
            )
            print(sentence, end="\n", flush=True)
            stream(audio_stream)
            full_text += sentence
        
        self.full_transcript.append({"role": "assistant", "content": full_text})

        self.start_transcription()


# Direct execution of the script
if __name__ == "__main__":
    try:
        print("Running Syri agent directly. For a better experience, use: python run.py")
        ai_voice_agent = AIVoiceAgent()
        print("Syri Voice Assistant started. Speak into your microphone...")
        ai_voice_agent.start_transcription()
        
        # Keep the program running
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nExiting Syri Voice Assistant...")
    except Exception as e:
        print(f"Error: {e}") 