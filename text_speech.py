import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import save

# Charger les variables d'environnement (ex: fichier .env)
load_dotenv()

# Initialize the client. 
# It will automatically look for the ELEVENLABS_API_KEY environment variable.
# You can also pass it explicitly if needed.
client = ElevenLabs(
    api_key=os.environ.get("ELEVENLABS_API_KEY", "your-api-key-here")
)

def generate_audio_bytes(text: str) -> bytes:
    """
    Transforms text to speech using ElevenLabs API and returns the audio bytes.
    """
    print(f"Generating speech for: '{text}'...")
    try:
        audio = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM", # Rachel voice ID
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        # client.generate returns a generator yielding bytes
        return b"".join(audio)
    except Exception as e:
        print(f"❌ Error generating speech: {e}")
        return b""

def transform_text_to_speech(text: str, output_filename: str = "output.mp3"):
    """
    Transforms text to speech using ElevenLabs API and saves it to a file.
    """
    print(f"Generating speech for: '{text}'...")
    
    try:
        # Generate the audio using the new client method
        audio = client.text_to_speech.convert(
            voice_id="21m00Tcm4TlvDq8ikWAM", # Rachel voice ID
            text=text,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        
        # Save the audio stream to a file
        save(audio, output_filename)
        print(f"✅ Audio successfully saved to {output_filename}")
        
    except Exception as e:
        print(f"❌ Error generating speech: {e}")

if __name__ == "__main__":
    # Example usage
    sample_text = "Hello! This is a demonstration of the ElevenLabs text to speech API."
    transform_text_to_speech(sample_text, "demo_speech.mp3")
