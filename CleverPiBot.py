# -*- coding: utf-8 -*-
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import logging
import os
import requests
from PIL import Image, ImageEnhance, ImageFont,  ImageDraw 
from io import BytesIO
import re 
from emoji import emojize, UNICODE_EMOJI
import ujson as json
import time
import socket

import secret_tokens

# replace these tokens with your tokens
admin_telegramID  = secret_tokens.myTelegramID
telegram_token = secret_tokens.myTelegramToken
faceAPI_token  = secret_tokens.myFaceAPI_token
# Msft cognitive Face API url replace with your local url
faceAPI_url = 'https://westcentralus.api.cognitive.microsoft.com/face/v1.0/detect'  

IamOnLinux = True
txt_yoffset = 28 

if IamOnLinux:
    font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf", 28, encoding="unic")
    download_folder = '/media/pi/ESD-USB/' # replace this with desired photo download folder
else:
    font = ImageFont.truetype("arial.ttf", 28)
    download_folder = './downloads/'      # replace this with desired photo download folder
  
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',level=logging.INFO)
logger = logging.getLogger(__name__)
def start(bot, update):
    user = update.message.from_user
    Message = "Hi there, I'm CleverPi bot. Send me a photo of yours. ⛈🎉🐧😊 \n"
    Message += "/start: start the bot.\n"
    Message += "/info: information about the bot.\n"
    Message += "/getip: returns the local network IP address\n"
    logger.info("Started chat with %s" , user.first_name)
    update.message.reply_text( Message )

def info_handler(bot, update):
    user = update.message.from_user
    Message =  "/start: start the bot.\n"
    Message += "/info: information about the bot.\n"
    Message += "/getip: returns the local network IP address\n"
    logger.info("Info requested by %s" , user.first_name)
    update.message.reply_text( Message )

def annotate_image(img_data ,headers,params):
    try:
        response=requests.post(faceAPI_url, data=img_data,headers=headers,params=params)
        print ('Face API Response:')
        faces = response.json()
        print (faces)
        image  = Image.open(BytesIO(img_data))
        image = ImageEnhance.Brightness(image).enhance(1.05)
        image = ImageEnhance.Contrast(image).enhance(1.1)
        image = ImageEnhance.Sharpness(image).enhance(1.4)
        for face in faces:
            draw = ImageDraw.Draw(image)
            fr = face["faceRectangle"]
            fa = face["faceAttributes"]
            origin = (fr["left"], fr["top"])
            lower_side = fr["top"] +  fr["width"]
            result_emotions_dict = fa["emotion"]  
            max_emotion_str = max(result_emotions_dict, key=result_emotions_dict.get).capitalize()   
            facialHair_dict = fa["facialHair"]
            facialHairMax_str = max(facialHair_dict, key=facialHair_dict.get)
            if  facialHair_dict[ facialHairMax_str  ] > 0.4 :
                facialHair_str = facialHairMax_str.capitalize()
            else:
                facialHair_str = "No beard"
            draw.text( (origin[0], lower_side)  ,"%s, %d"%(fa["gender"].capitalize(), fa["age"]) ,fill= (255,0,0 ),font=font)
            draw.text( (origin[0], lower_side+ txt_yoffset) , max_emotion_str  ,fill= (255,0,0 ),font=font)
            draw.text( (origin[0], lower_side+2*txt_yoffset) ,fa["glasses"].capitalize() ,fill= (255,0,0 ),font=font)
            draw.text( (origin[0], lower_side+3*txt_yoffset) , facialHair_str   ,fill= (255,0,0 ),font=font)
            draw.rectangle( [origin[0], origin[1] , origin[0]+fr["width"], origin[1]+fr["height"]], fill=None, outline= (255,0,0))
        return image 
    except Exception as e:
        print('Error:')
        print(e)
        return image 

def photo_handler(bot, update):
    user = update.message.from_user
    photo_id  = update.message.photo[-1].file_id
    photo_file = bot.get_file(photo_id)
    update.message.reply_text('Let me take a look at your photo...')
    logger.info("Received photo from %s: %s", user.first_name,  str( photo_id) )
    img_path =  download_folder + str( photo_id) 
    photo_file.download( img_path   + ".jpg" )
    with open(  img_path   + ".jpg" , 'rb' ) as f:
        img_data = f.read()
        FaceAPI_headers = { 'Ocp-Apim-Subscription-Key': faceAPI_token , 'Content-Type': 'application/octet-stream' }
        FaceAPI_params = {'returnFaceId': 'true', 'returnFaceLandmarks': 'false','returnFaceAttributes': 'age,gender,glasses,emotion,facialHair'}
    #    'returnFaceAttributes': 'age,gender,smile,facialHair,glasses,emotion,hair,makeup,occlusion,accessories,blur,exposure,noise'    
        img = annotate_image(img_data ,FaceAPI_headers,FaceAPI_params)
        img_edited_path = img_path + '_edit.jpg' 
        img.save( img_edited_path, "JPEG")

    with open(img_edited_path, 'rb') as f:
        bot.send_photo(chat_id=update.message.chat_id, photo=f, timeout=50)
    os.remove(img_path  + '.jpg' )   # remove unmodified photo
    # os.remove(img_edited_path)     # remove modified photo
    update.message.reply_text('Gorgeous photo!')

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)

def getIP_command(bot, update):
    user = update.message.from_user
    if (admin_telegramID == user.id ):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        strIP  = s.getsockname()[0]
        s.close()
        msg = "Your IP adress is: " + str(strIP)
        bot.send_message(chat_id=update.message.chat_id, text=msg   )
        logger.info("IP adress requested by %s",  user.first_name   )
    else:
        bot.send_message(chat_id=update.message.chat_id, text="No permission." )
        logger.info("Unauthorized user requested IP adress %s",  user.first_name   )

def is_emoji(s):
    return s in UNICODE_EMOJI

def text_handler(bot, update):
        message = update.message.text
        user = update.message.from_user
        logger.info("New message by %s : %s", user.first_name, message )
        msg_stripped  = message.lower() 
        msg_stripped = re.sub(r'([^\s\w]|_)+', '', msg_stripped)  # remove all special characters
        msg_stripped = re.sub(r'([^\D]|_)+', '', msg_stripped)    # remove all digits characters

        # check if message is a greeting
        greetings_list = [ 'hi'  ,'hey', 'hello', 'greetings' , 'hoi',  "sup" ]
        if any(set(msg_stripped.split()) & set(greetings_list)):
            bot.send_message(chat_id=update.message.chat_id, text='Hello, whats up?')
        else: # try to turn message into smiley to send back
            try:
                replace_dictionary  = {'happy': 'smiley' , 'sad':  'persevere'  , 'surprised':  'hushed' , 'neutral':  'neutral_face'  }
                # replace words using replace_dictionary for more emoji responses
                msg_modified = re.compile("|".join(replace_dictionary.keys())).sub(lambda m: replace_dictionary[re.escape(m.group(0))], msg_stripped)
                msg_emoji = [":" + msg + ":" for msg in msg_modified.split() ]
                emojis = emojize(" ".join(msg_emoji) , use_aliases=True)
                only_emojis = []
                for msg in emojis.split():
                    if is_emoji(msg):
                        only_emojis.append(msg)
                if only_emojis:        
                    bot.send_message(chat_id=update.message.chat_id, text= " ".join(only_emojis) )
            except:
                logger.warning('Emoji update "%s" by "%s" caused error ' , message ,  user.first_name )

def unknown(bot, update):
    user = update.message.from_user
    command = update.message.text
    bot.send_message(chat_id=update.message.chat_id, text="Sorry, I didn't understand that command.")
    logger.info("Unknown command by %s : %s",  user.first_name , command  )

def main():
    updater = Updater(telegram_token)
    dp = updater.dispatcher # Get the dispatcher to register handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("info", info_handler))
    dp.add_handler(CommandHandler("getip", getIP_command))
    dp.add_handler(MessageHandler(Filters.text, text_handler))
    dp.add_handler(MessageHandler(Filters.photo, photo_handler))
    dp.add_handler(MessageHandler(Filters.command, unknown))
    dp.add_error_handler(error)
    print ('Bot started ...')
    updater.start_polling()
    updater.idle()
    
if __name__ == '__main__':
    main()