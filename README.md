# **Gemini Bot**

This code provides a Python implementation of a Telegram Chatbot powered by Vertex AI's generative models. The bot uses the Telethon Python library to interact with the Telegram Bot API and Google Cloud's Vertex AI API for generative models.

## **Installation**

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/yourusername/Gemini-Bot.git
cd Gemini-Bot
```

Install the required packages:

```bash
pip install -r requirements.txt
```

## **Configuration**

The bot requires Google Cloud credentials and Telegram Bot API credentials to function. You must create a **`config.py`** file in the same directory as the **`gemini-bot.py`** file and include the following variables:

```python
# config.py
API_ID = 'your_telegram_api_id'
API_HASH = 'your_telegram_api_hash'
BOT_TOKEN = 'your_telegram_bot_token'
project_id = 'your_google_cloud_project_id'
location = 'your_google_cloud_location'
session_name_bot = 'gemini_bot'
```

You can obtain a Telegram API ID and hash by following the instructions [here](https://core.telegram.org/api/obtaining_api_id). To obtain a bot token, you can talk to [BotFather](https://telegram.me/botfather) on Telegram. For Google Cloud credentials, follow the instructions on the [Google Cloud Documentation](https://cloud.google.com/vertex-ai/docs/python-sdk/use-vertex-ai-python-sdk).

## **Usage**

To start the bot, run the following command in your terminal:

```bash
python gemini-bot.py
```

This will start the bot and wait for user queries. Once the bot is running, you can interact with it by sending messages to it in Telegram.

The bot will respond to any message it receives by generating a response using the Vertex AI API and sending it back to the user. The bot will continue generating responses until the conversation times out or the user clicks the "Stop and reset conversation" button.