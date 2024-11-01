import os
import requests
from pyrogram import Client, filters
from g4f.client import Client as G4FClient

# Initialize Pyrogram Client
app = Client("my_bot", api_id=29049827, api_hash="16039b7254c83bed8df1038e4139b1b9", bot_token="7297397883:AAFo7xlynx-Vr1ngEM5jt_DTu25SmKOLuFw")

# Initialize g4f Client
g4f_client = G4FClient()

@app.on_message(filters.command("start"))
async def start(client, message):
    await message.reply("Hello! Send me a prompt, and I'll generate an image for you.")

@app.on_message(filters.text & ~filters.command("start"))
async def generate_image(client, message):
    user_prompt = message.text
    
    # Use the asynchronous image generation
    response = await g4f_client.images.async_generate(
        model="playground-v2.5",
        prompt=user_prompt
    )

    # Check if the response contains a URL
    if response and response.data:
        image_url = response.data[0].url
        image_path = "generated_image.jpg"

        # Download the image
        image_data = requests.get(image_url)
        with open(image_path, "wb") as f:
            f.write(image_data.content)

        # Send the image to the user
        await message.reply_photo(photo=image_path, caption="Here's your generated image!")

        # Clean up the downloaded file
        os.remove(image_path)
    else:
        await message.reply("Sorry, I couldn't generate an image. Please try again.")

# Run the bot
app.run()
