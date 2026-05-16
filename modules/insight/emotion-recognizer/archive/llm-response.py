#!/usr/bin/env python3
"""
This script demonstrates how to use gpt-5 model to generate answers to user prompts.
Requirements:
- OpenAI Python library (v1.0.0 or higher)
- python-dotenv library for loading .env files
- Valid apiGPTeal test key stored in environment variable. 
  - If you do not have key, visit: https://share.merck.com/spaces/EG/pages/1759994187/apiGPTeal+Onboarding
Usage:
1. Ensure your API key is set in the .env file or as an environment variable
2. Note that this example uses the TEST environment of apiGPTeal.
3. Run the script
"""

import os
import sys
import openai
from dotenv import load_dotenv

def setup_openai_api():
    # Load environment variables from .env file
    load_dotenv()
    
    # Set up API configuration
    openai.api_type = "azure"
    openai.azure_endpoint = "https://iapi-test.merck.com/gpt/libsupport"
    openai.api_version = "2024-10-21"
    
    # Get API key from environment variable
    api_key = os.getenv("XMerckAPIKey")
    if not api_key:
        raise ValueError("API key not found. Please set XMerckAPIKey in your environment variables and make sure you are using the TEST Key.")
    openai.api_key = api_key
    
    # Check OpenAI library version
    if openai.__version__.split(".")[0] == "0":
        raise Exception(
            "Please update OpenAI library to version >=1.0.0 (pip install openai --upgrade)"
        )

def create_chat_completion(user_message):
    """
    Create a chat completion using the full GPT-5 model (gpt-5-2025-08-07).
    
    Args:
        user_message (str): The user's message to send to the API
        
    Returns:
        object: The API response object
        
    Example:
        response = create_chat_completion("What is artificial intelligence?")
    """
    try:
        response = openai.chat.completions.create(
            # Visit https://share.merck.com/spaces/EG/pages/1827607209/Model+Catalog to learn all the available models
            model="gpt-5-2025-08-07",
            
            # The conversation history as a list of messages
            messages=[
                {"role": "user", "content": user_message},
            ],
            
            max_completion_tokens=2000,   
        )
        return response
    except Exception as e:
        print(f"Error creating chat completion: {e}")
        sys.exit(1)

def extract_message_content(response):
    """
    Extract the message content from the API response.
    
    Args:
        response: The API response object
        
    Returns:
        str: The extracted message content
    """
    return response.choices[0].message.content

def main():
    """
    Main function to demonstrate the GPT-5 chat completion API.
    """
    # Set up the API
    setup_openai_api()
    
    # Create a chat completion
    user_query = "What is the meaining of life?"
    print(f"Sending the prompt to model through apigpteal..: '{user_query}'")
    
    response = create_chat_completion(user_query)
    
    # Print the full response object (for debugging/educational purposes)
    print("\n--- Full API Response ---")
    print(response)
    
    # Extract and print just the message content
    message = extract_message_content(response)
    print("\n--- GPT-5 Response ---")
    print(message)

if __name__ == "__main__":
    main()