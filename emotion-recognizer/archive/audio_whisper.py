#!/usr/bin/env python3
"""
apiGPTeal Whisper Transcription Example

This script demonstrates how to use the apiGPTeal API with the Whisper model
to transcribe audio files to text. Whisper can process various audio formats and
automatically detect the spoken language.

Supported audio formats: mp3, mp4, mpeg, mpga, m4a, wav, webm (max 25MB)

Requirements:
- requests Python library
- Valid apiGPTeal test key stored in environment variable

Usage:
1. Ensure your API key is set in the environment variables
2. Have an audio file ready (e.g., apigpteal_sample.m4a)
3. Run the script
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

def setup_api():
    """
    Get the API key from environment.
    
    Raises:
        ValueError: If API key is not found
    """
    load_dotenv()
    api_key = os.getenv("XMerckAPIKey")
    if not api_key:
        raise ValueError("API key not found. Please set XMerckAPIKey in your environment variables and make sure you are using the TEST Key.")
    return api_key

def transcribe_audio(audio_path, api_key):
    """
    Transcribe audio using the Whisper model via apiGPTeal.
    
    Args:
        audio_path (str): Path to the audio file
        api_key (str): The apiGPTealkey
        
    Returns:
        dict: The API response containing the transcription
        
    Example:
        response = transcribe_audio("apigpteal_sample.m4a", api_key)
    """
    try:
        # API configuration
        api_root = "https://iapi-test.merck.com/gpt/v2"
        model = "whisper-1"
        api_version = "2024-10-21"
        url = f"{api_root}/{model}/audio/transcriptions"
        
        # Headers
        headers = {
            "X-Merck-APIKey": api_key
        }
        
        # Prepare files and data
        files = {
            "file": open(audio_path, "rb")
        }
        data = {
            "response_format": "verbose_json",
            "language": "en"
        }
        
        # Send the request
        print(f"Transcribing audio: {audio_path}")
        response = requests.post(url, params={"api-version": api_version}, headers=headers, files=files, data=data)
        
        # Check if the request was successful
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        sys.exit(1)

def main():
    """
    Main function to demonstrate audio transcription.
    """
    # Setup
    api_key = setup_api()
    
    # Audio file path
    audio_path = "apigpteal_sample.m4a"
    
    # Transcribe
    response = transcribe_audio(audio_path, api_key)
    
    # Print response
    print("\n--- Transcription Result ---")
    print(json.dumps(response, indent=4))
    
    # Extract and print key info
    if "text" in response:
        print("\nTranscribed Text:")
        print(response["text"])
    if "language" in response:
        print(f"\nDetected Language: {response['language']}")

if __name__ == "__main__":
    main()