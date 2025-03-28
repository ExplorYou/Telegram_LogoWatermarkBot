import telebot
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import psycopg2
import os
import urllib.parse as urlparse

# Bot token
bot = telebot.TeleBot("7512402960:AAFTSAXRATbbcgIL5iE8Ug3e0G6_B0a3AcU")

# Database setup (Postgres)
DATABASE_URL = os.getenv('DATABASE_URL')
url = urlparse.urlparse(DATABASE_URL)
conn = psycopg2.connect(
    dbname=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (chat_id TEXT_PRIMARY_KEY, logo_path TEXT, text_logo TEXT, position TEXT, channel_id TEXT, google_download INTEGER)''')
conn.commit()

# Default channel set karna
#DEFAULT_CHANNEL = "https://t.me/StreemCode1"
#DEFAULT_CHANNEL_ID = ""

# Position options
POSITIONS = {
    "top-left": (0, 0),
    "top-middle": None,
    "top-right": None,
    "middle-left": None,
    "middle-middle": None,
    "middle-right": None,
    "bottom-left": None,
    "bottom-middle": None,
    "bottom-right": None
}

# Google se image download karne ka function
def download_image_from_google(query):
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}&tbm=isch"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        start = response.text.find('img src="') + 9
        end = response.text.find('"', start)
        img_url = response.text[start:end]
        if img_url.startswith("http"):
            img_response = requests.get(img_url, timeout=10)
            return BytesIO(img_response.content)
        return None
    except Exception as e:
        print(f"Error downloading image from Google: {e}")
        return None

# Text ko image mein convert karne ka function
def create_text_logo(text):
    img = Image.new('RGBA', (300, 200), (0, 0, 0, 0))  # Size 300x200
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 30)  # Font size adjust kiya
    except:
        font = ImageFont.load_default()
    
    # Text ke saath shadow aur border
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width, text_height = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
    text_x = (300 - text_width) // 2
    text_y = (200 - text_height) // 2
    
    # Shadow (Red: 255, 0, 0, 255)
    shadow_offset = 2
    draw.text((text_x + shadow_offset, text_y + shadow_offset), text, font=font, fill=(255, 0, 0, 255))  # Red shadow
    
    # Border (Black: 0, 0, 0, 255) - Multiple passes to create a thicker outline
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx != 0 or dy != 0:
                draw.text((text_x + dx, text_y + dy), text, font=font, fill=(0, 0, 0, 255))  # Black border
    
    # Main text (White: 255, 255, 255, 255)
    draw.text((text_x, text_y), text, font=font, fill=(255, 255, 255, 255))  # White text
    
    return img

# Database query ke liye helper function
def get_user_settings(chat_id):
    cursor.execute("SELECT logo_path, text_logo, position, channel_id, google_download FROM users WHERE chat_id = %s OR channel_id = %s", (chat_id, chat_id))
    return cursor.fetchone()

# Welcome message
@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    cursor.execute("INSERT INTO users (chat_id, channel_id, position, google_download) VALUES (%s, %s, %s, %s) ON CONFLICT (chat_id) DO NOTHING",
                   (chat_id, DEFAULT_CHANNEL_ID, "bottom-right", 0))
    conn.commit()
    bot.reply_to(message, "<b>/start - Toh chaliye Shuru karte hai Maza aayengha\n"
                          "/setlogo - Image logo set karo\n"
                          "/settextaslogo - Text logo set karo\n"
                          "/sc - Channel ya group connect karo (@username ya link)\n"
                          "/GIDS - Google Image Download set karo (on/off)\n"
                          "Channel/Group mein post karo, main logo laga dunga!\n\n"
                          "My Devloper\n"
                          "Hindi:\n"
                          "Bhai/Bahen, Yahan Aapko Saari Movies, Web Series Aur Anime Mil Jayengi!\n"
                          "Direct File Format: @FileFormatHere (Mkv, Mp4, Avi, Mov, Wmv, Aur Bhi)\n"
                          "Terabox Link: @Req_Fullfil (Sirf Link, Turant Milega)\n\n"
                          "English:\n"
                          "Brother/Sister, You’ll Find All Movies, Web Series, And Anime Right Here!\n"
                          "Direct File Format: @FileFormatHere (Mkv, Mp4, Avi, Mov, Wmv, And More)\n"
                          "Terabox Link: @Req_Fullfil (Just The Link, Delivered Instantly)</b>", parse_mode="HTML")

# Image logo set karne ka command
@bot.message_handler(commands=['setlogo'])
def set_logo(message):
    chat_id = str(message.chat.id)
    bot.reply_to(message, "Apna logo image (PNG recommended) bhejo!")
    bot.register_next_step_handler(message, save_logo)

def save_logo(message):
    chat_id = str(message.chat.id)
    if message.photo:
        file_id = message.photo[-1].file_id
        try:
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
            response = requests.get(file_url, timeout=10)
            response.raise_for_status()
            
            logo_path = f"logos/{chat_id}.png"
            os.makedirs("logos", exist_ok=True)
            with open(logo_path, "wb") as f:
                f.write(response.content)
            
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")
                logo.save(logo_path, "PNG")
                cursor.execute("UPDATE users SET logo_path = %s, text_logo = NULL, position = %s, google_download = %s WHERE chat_id = %s",
                               (logo_path, "bottom-right", 0, chat_id))
                conn.commit()
                markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
                for pos in POSITIONS.keys():
                    markup.add(pos)
                bot.reply_to(message, f"Image logo set ho gaya! Chat ID: {chat_id}. Ab position choose karo:", reply_markup=markup)
                bot.register_next_step_handler(message, save_position)
            else:
                bot.reply_to(message, "Logo save nahi hua, bhai! Dobara try karo.")
        except requests.RequestException as e:
            bot.reply_to(message, f"Error downloading logo: {e}")
        except Exception as e:
            bot.reply_to(message, f"Kuch galat ho gaya: {e}")
    else:
        bot.reply_to(message, "Image bhejo bhai, text nahi!")

# Text logo set karne ka command
@bot.message_handler(commands=['settextaslogo'])
def set_text_logo(message):
    chat_id = str(message.chat.id)
    bot.reply_to(message, "Apna text logo bhejo (e.g., 'My Brand')!")
    bot.register_next_step_handler(message, save_text_logo)

def save_text_logo(message):
    chat_id = str(message.chat.id)
    text = message.text.strip()
    if text:
        cursor.execute("UPDATE users SET logo_path = NULL, text_logo = %s, position = %s, google_download = %s WHERE chat_id = %s",
                       (text, "bottom-right", 0, chat_id))
        conn.commit()
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
        for pos in POSITIONS.keys():
            markup.add(pos)
        bot.reply_to(message, f"Text logo '{text}' set ho gaya! Chat ID: {chat_id}. Ab position choose karo:", reply_markup=markup)
        bot.register_next_step_handler(message, save_position)
    else:
        bot.reply_to(message, "Kuch text bhejo bhai!")

# Position set karne ka function
def save_position(message):
    chat_id = str(message.chat.id)
    position = message.text.lower()
    if position in POSITIONS:
        cursor.execute("UPDATE users SET position = %s WHERE chat_id = %s", (position, chat_id))
        conn.commit()
        bot.reply_to(message, f"Position set to {position}! Chat ID: {chat_id}. Ab /sc se channel ya group set karo agar chaho.")
    else:
        bot.reply_to(message, "Valid position choose karo: top-left, top-middle, etc.")

# Channel/Group set karne ka command
@bot.message_handler(commands=['sc'])
def set_channel(message):
    chat_id = str(message.chat.id)
    bot.reply_to(message, "Apne channel ya group ka @username ya link bhejo (e.g., @MyChannel ya https://t.me/...)")
    bot.register_next_step_handler(message, save_channel)

def save_channel(message):
    chat_id = str(message.chat.id)
    input_text = message.text.strip()
    try:
        if input_text.startswith('@'):
            channel_info = bot.get_chat(input_text)
            channel_id = str(channel_info.id)
        elif input_text.startswith('https://t.me/'):
            invite_link = input_text
            join_result = bot.join_chat(invite_link)
            channel_id = str(join_result.id)
        else:
            bot.reply_to(message, "Sahi @username ya https://t.me/ link bhejo!")
            return
        
        cursor.execute("UPDATE users SET channel_id = %s WHERE chat_id = %s", (channel_id, chat_id))
        conn.commit()
        bot.reply_to(message, f"Channel/Group set ho gaya! ID: {channel_id}. Ab post karo, main handle kar lunga!")
    except Exception as e:
        bot.reply_to(message, f"Channel/Group set karne mein error: {e}. Sahi input bhejo ya admin rights check karo!")

# Google Image Download Set command
@bot.message_handler(commands=['GIDS'])
def set_google_download(message):
    chat_id = str(message.chat.id)
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add("On", "Off")
    bot.reply_to(message, "Google Image Download on karna hai ya off?", reply_markup=markup)
    bot.register_next_step_handler(message, save_google_setting)

def save_google_setting(message):
    chat_id = str(message.chat.id)
    choice = message.text.lower()
    if choice == "on":
        google_download = 1
    elif choice == "off":
        google_download = 0
    else:
        bot.reply_to(message, "Sirf 'On' ya 'Off' choose karo!")
        return
    cursor.execute("UPDATE users SET google_download = %s WHERE chat_id = %s", (google_download, chat_id))
    conn.commit()
    bot.reply_to(message, f"Google Image Download set to: {choice.upper()}")

# Channel/Group posts aur private chats ke liye image handler
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = str(message.chat.id)
    print(f"Photo received in chat: {chat_id}")
    
    result = get_user_settings(chat_id)
    if result and (result[0] or result[1]):  # logo_path ya text_logo mein se koi ek
        logo_path, text_logo, position, channel_id, google_download = result
        print(f"Logo found: {logo_path}, Text Logo: {text_logo}, Position: {position}, Channel ID: {channel_id}, Google Download: {google_download}")
        
        if logo_path and not os.path.exists(logo_path):
            print(f"Logo file missing: {logo_path}")
            bot.send_message(chat_id, "Logo file nahi mili! /setlogo se dobara set karo.")
            return
        
        file_id = message.photo[-1].file_id
        original_caption = message.caption if message.caption else ""
        bold_caption = f"<b>{original_caption}</b>" if original_caption else ""
        
        try:
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{bot.token}/{file_info.file_path}"
            response = requests.get(file_url, timeout=10)
            response.raise_for_status()
            
            input_image = Image.open(BytesIO(response.content)).convert("RGBA")
            
            if logo_path:
                logo = Image.open(logo_path).convert("RGBA")
            elif text_logo:
                logo = create_text_logo(text_logo)
            logo = logo.resize((300, 200))  # Logo size 300x200

            img_width, img_height = input_image.size
            logo_width, logo_height = logo.size
            if position == "top-left":
                pos = (0, 0)
            elif position == "top-middle":
                pos = ((img_width - logo_width) // 2, 0)
            elif position == "top-right":
                pos = (img_width - logo_width, 0)
            elif position == "middle-left":
                pos = (0, (img_height - logo_height) // 2)
            elif position == "middle-middle":
                pos = ((img_width - logo_width) // 2, (img_height - logo_height) // 2)
            elif position == "middle-right":
                pos = (img_width - logo_width, (img_height - logo_height) // 2)
            elif position == "bottom-left":
                pos = (0, img_height - logo_height)
            elif position == "bottom-middle":
                pos = ((img_width - logo_width) // 2, img_height - logo_height)
            elif position == "bottom-right":
                pos = (img_width - logo_width, img_height - logo_height)

            final_image = input_image
            if google_download and original_caption:
                google_image_data = download_image_from_google(original_caption)
                if google_image_data:
                    google_image = Image.open(google_image_data).convert("RGBA")
                    google_image = google_image.resize(input_image.size)
                    google_image.paste(logo, pos, logo)
                    final_image = google_image
                else:
                    final_image.paste(logo, pos, logo)
            else:
                final_image.paste(logo, pos, logo)

            output = BytesIO()
            final_image.save(output, format="PNG")
            output.seek(0)
            
            # Channel ya group mein edit karo
            if str(chat_id) == str(channel_id):
                try:
                    bot.edit_message_media(
                        media=telebot.types.InputMediaPhoto(output, caption=bold_caption, parse_mode="HTML"),
                        chat_id=chat_id,
                        message_id=message.message_id
                    )
                    print(f"Edited post in channel/group {chat_id}")
                except Exception as e:
                    print(f"Error editing message in channel: {e}")
                    bot.send_message(chat_id, "Mujhe channel mein edit karne ke permissions do!")
            else:
                bot.send_photo(chat_id, output, caption=bold_caption, parse_mode="HTML")
                print(f"Watermarked image sent to {chat_id}")
        except requests.RequestException as e:
            print(f"Error downloading image: {e}")
        except Exception as e:
            print(f"Error processing image: {e}")
    else:
        print(f"No logo set for chat {chat_id}")
        if message.chat.type in ["channel", "group", "supergroup"]:
            bot.send_message(chat_id, "Pehle mujhe private mein /setlogo ya /settextaslogo se setup karo!")

# Bot ko chalao
if __name__ == "__main__":
    print("Bot shuru ho raha hai...")
    bot.polling()
