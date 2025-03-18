import assemblyai as aai
from elevenlabs.client import ElevenLabs
from elevenlabs import stream
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
        self.client = ElevenLabs(
            api_key=elevenlabs_api_key
        )

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
        
        # Prepare messages in the format expected by Claude API
        messages = []
        for message in self.full_transcript:
            messages.append({"role": message["role"], "content": message["content"]})
        
        from portkey_ai import Portkey

        # Initialize Portkey client
        portkey = Portkey(
            api_key=os.getenv("PORTKEY_API_KEY"),
            virtual_key=os.getenv("PORTKEY_VIRTUAL_KEY_ANTHROPIC")
        )
        
        # Get response from Claude 3.7 Sonnet
        response = portkey.chat.completions.create(
            messages=messages,
            model="claude-3-7-sonnet-latest",
            stream=True
        )

        text_buffer = ""
        full_text = ""
        
        # Process the streaming response
        for chunk in response:
            if chunk.choices[0].delta.content:
                text_buffer += chunk.choices[0].delta.content
                if text_buffer.endswith('.') or text_buffer.endswith('!') or text_buffer.endswith('?'):
                    audio_stream = self.client.generate(
                        text=text_buffer,
                        model="eleven_turbo_v2",
                        stream=True
                    )
                    print(text_buffer, end="\n", flush=True)
                    stream(audio_stream)
                    full_text += text_buffer
                    text_buffer = ""

        if text_buffer:
            audio_stream = self.client.generate(
                text=text_buffer,
                model="eleven_turbo_v2",
                stream=True
            )
            print(text_buffer, end="\n", flush=True)
            stream(audio_stream)
            full_text += text_buffer

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