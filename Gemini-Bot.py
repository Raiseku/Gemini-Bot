# Importing Libraries
import telethon # Library to interact with Telegram's API as a user or through a bot account 
from telethon.tl.custom import Button
from telethon import TelegramClient, events

import asyncio # Provides infrastructure for writing asynchronous code using coroutines.

# Imports for handling images and bytes
from io import BytesIO
from PIL import Image

import config # Custom file containing configuration settings for the bot.

# Import necessary modules from the vertexai library
import vertexai
from vertexai.generative_models._generative_models import HarmCategory, HarmBlockThreshold
from vertexai.preview.generative_models import (
    GenerativeModel,
    ChatSession,
    Part
)

# Configuration settings for the generative model
generation_config = {
    "temperature": 0.7,            # Controls the randomness of generated output (lower values make output more deterministic)
    "top_p": 1,                    # Top-p nucleus sampling parameter (controls the probability mass to consider for sampling)
    "top_k": 1,                    # Top-k sampling parameter (controls the number of highest probability tokens to consider for sampling)
    "max_output_tokens": 2048,     # Maximum number of tokens to generate in the output
}

# Safety settings to control harmful content blocking thresholds
safety_settings = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,        # No blocking for dangerous content
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,             # No blocking for hate speech
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,              # No blocking for harassment
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,       # No blocking for sexually explicit content
}

# Initialize Vertex AI with project and location
vertexai.init(project=config.project_id, location=config.location)

# Initialize generative models
model = GenerativeModel("gemini-pro", generation_config=generation_config, safety_settings=safety_settings)
vision_model = GenerativeModel("gemini-pro-vision", generation_config=generation_config, safety_settings=safety_settings)

# Configure Telegram client
client = TelegramClient(config.session_name_bot, config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)

# Define button templates
keyboard_stop = [[Button.inline("Stop and reset conversation", b"stop")]]

# Define helper function to retrieve a message from a conversation and handle button clicks
async def send_question_and_retrieve_result(prompt, conv, keyboard):
    """
    Sends a question to the user and retrieves their response.

    Args:
        prompt (str): The question to ask the user.
        conv (telethon.client.conversations.Conversation): The conversation object to use for sending the message.
        keyboard (list): The keyboard to send with the message.

    Returns:
        Tuple[Union[events.callbackquery.CallbackQuery.Event, str], telethon.types.Message]: A tuple containing the user's response and the message object.
    """
    # Send the prompt with the keyboard to the user and store the sent message object
    message = await conv.send_message(prompt, buttons = keyboard)
    
    loop = asyncio.get_event_loop()
    
    # Create tasks to wait for the user to respond or tap a button
    task1 = loop.create_task(
        conv.wait_event(events.CallbackQuery())
    )
    task2 = loop.create_task(
        conv.get_response()
    )

    # Wait for the user to respond or tap a button using asyncio.wait()
    done, _ = await asyncio.wait({task1, task2}, return_when=asyncio.FIRST_COMPLETED)
    
    # Retrieve the result of the completed coroutine and delete the sent message
    result = done.pop().result()
    await message.delete()
    
    # Return the user's response or None if they tapped a button
    if isinstance(result, events.CallbackQuery.Event):
        return None
    else:
        return result


# Define the main chatbot handler
@client.on(events.NewMessage(pattern="(?i)/chat"))
async def handle_chat_command(event):
    """
    Starts a new conversation with the user.

    Args:
        event (telethon.events.NewMessage): The event that triggered this function.
    """

    def get_chat_response(chat: ChatSession, prompt: str) -> str:
        """
        Sends a prompt to the chat model and returns the response.

        Args:
            chat (vertexai.preview.generative_models.ChatSession): The chat session.
            prompt (str): The prompt to send to the chat model.

        Returns:
            str: The response from the chat model.
        """
        response = chat.send_message(prompt) 
        return response.text

    # Get the sender's ID
    SENDER = event.sender_id

    try:
        # Start a conversation
        async with client.conversation(await event.get_chat(), exclusive=True, timeout=600) as conv:
            # Create an empty history to store chat history
            chat = model.start_chat(history=[])

            # Keep asking for input and generating responses until the conversation times out or the user clicks the stop button
            while True:
                # Prompt the user for input
                prompt = "Provide your input to Gemini Bot..."
                user_input = await send_question_and_retrieve_result(prompt, conv, keyboard_stop)
                
                # Check if the user clicked the stop button
                if user_input is None:
                    # If the user clicked the stop button, send a prompt to reset the conversation
                    prompt = "Conversation will be reset. Type /chat to start a new one!"
                    await client.send_message(SENDER, prompt)
                    break
                else:
                    user_input = user_input.message.strip()
                    # Send a "I'm thinking message..."
                    prompt = "Received! I'm thinking about the response..."
                    thinking_message = await client.send_message(SENDER, prompt)

                    # Retrieve Gemini response
                    response = (get_chat_response(chat, user_input))

                    # Delete the Thinking message
                    await thinking_message.delete()
                    
                    # Send the response to the user
                    await client.send_message(SENDER, response, parse_mode='Markdown')


    except asyncio.TimeoutError:
        # Conversation timed out
        await client.send_message(SENDER, "<b>Conversation ended✔️</b>\nIt's been too long since your last response.", parse_mode='html')
        return

    except telethon.errors.common.AlreadyInConversationError:
        # User already in conversation
        pass

    except Exception as e: 
        # Something went wrong
        await client.send_message(SENDER, "<b>Conversation ended✔️</b>\nSomething went wrong.", parse_mode='html')
        return


@client.on(events.NewMessage(pattern="(?i)/image"))
async def handle_image_command(event):
    """
        Handles the /image command, where the bot requests the user to send an image
        and then processes the image using a vision model.

        Args:
            event (telethon.events.NewMessage): The event that triggered this function.
    """

    # Get the sender's ID
    SENDER = event.sender_id
    try:
        # Start a conversation to handle image processing
        async with client.conversation(await event.get_chat(), exclusive=True, timeout=600) as conv:
            prompt = "Send me an image, and I'll tell you what is shown inside."
            
            # Ask the user for input and retrieve the response
            user_input = await send_question_and_retrieve_result(prompt, conv, keyboard_stop)
            
             # Check if the user clicked the stop button
            if user_input is None:
                await client.send_message(SENDER, "Conversation will be reset. Type /image to send me another image.", parse_mode='Markdown')
                return 
            else: 
                # Check if the user provided a valid image
                if user_input.photo:
                    
                    prompt = "Received! I'm thinking about the response..."
                    thinking_message = await client.send_message(SENDER, prompt)
                    
                    photo_entity = user_input.photo
    
                     # Download the image and open it using PIL
                    photo_path  = await client.download_media(photo_entity, file="images/")
                    image = Image.open(photo_path)
    
                    # Convert the image to JPEG format
                    image_buf = BytesIO()
                    image.save(image_buf, format="JPEG")
                    image_bytes = image_buf.getvalue()
                    
                    # Generate content using the vision model
                    response = vision_model.generate_content(
                        [
                            Part.from_data(
                                image_bytes, mime_type="image/jpeg"
                            ),
                            "What is shown in this image?",
                        ]
                    )
    
                    # Delete the Thinking message
                    await thinking_message.delete()
    
                    # Send the response to the user
                    await client.send_message(SENDER, response.text, parse_mode='Markdown')
    
                else:
                    # Inform the user that the input is not valid
                    await client.send_message(SENDER, "Input not valid. Please send me an image after using the /image command.", parse_mode='Markdown')
                    
    except asyncio.TimeoutError:
        # Conversation timed out
        await client.send_message(SENDER, "<b>Conversation ended✔️</b>\nIt's been too long since your last response.", parse_mode='html')
        return

    except telethon.errors.common.AlreadyInConversationError:
        # User already in conversation
        pass

    except Exception as e: 
        # Something went wrong
        await client.send_message(SENDER, "<b>Conversation ended✔️</b>\nSomething went wrong.", parse_mode='html')
        return


@client.on(events.NewMessage(pattern="(?i)/start"))
async def handle_start_command(event):
    text = """Hello there! I'm Gemini 🤖, your friendly chatbot. I can answer your questions in a conversational manner and even recognize the contents of images. Let's get started!
    
    /chat: Initiate a chat with me.
    /image: Share an image and learn about its contents.
    
Feel free to explore and ask me anything!"""
    
    await client.send_message(event.sender_id, text)

## Main function
if __name__ == "__main__":
    print("Bot Started...")    
    client.run_until_disconnected() # Start the bot!


