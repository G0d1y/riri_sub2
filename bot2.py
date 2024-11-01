import os
import requests
from pyrogram import Client, filters
from g4f.client import Client as G4FClient
import json

with open('config2.json') as config_file:
    config = json.load(config_file)

api_id = int(config['api_id'])
api_hash = config['api_hash']
bot_token = config['bot_token']

app = Client("Image_Generator", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

g4f_client = G4FClient()

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello! Send me a prompt, and I'll generate an image for you.")

@app.on_message(filters.text & ~filters.command("start"))
async def generate_image(client, message):
    user_prompt = message.text
    response = g4f_client.images.generate(
        model="playground-v2.5",
        prompt=user_prompt
    )

    if response and response.data:
        image_url = response.data[0].url
        image_path = "generated_image.jpg"

        response = requests.get(image_url)
        with open(image_path, "wb") as f:
            f.write(response.content)

        await message.reply_photo(photo=image_path, caption="Here's your generated image!")

        os.remove(image_path)
    else:
        await message.reply("Sorry, I couldn't generate an image. Please try again.")

app.run()
