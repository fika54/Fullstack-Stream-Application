from TikTokLive import TikTokLiveClient
from TikTokLive.events import CommentEvent, JoinEvent, ConnectEvent, DisconnectEvent
from twitchAPI.chat import Chat, EventData,ChatMessage, ChatSub, ChatCommand
from twitchAPI.type import AuthScope, ChatEvent
from twitchAPI.oauth import UserAuthenticator
from twitchAPI.twitch import Twitch
import app.MessageSort as MessageSort
import random
import app.functions.dontleak as dontleak
import asyncio


#Connection to tiktok chat
client = TikTokLiveClient(unique_id="@f1kayo54")

#Connection to twitch chat
APP_ID = dontleak.client_id
APP_SECRET = dontleak.client_secret
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT, AuthScope.CHANNEL_MANAGE_BROADCAST]
TARGET_CHANNEL = 'fika54'

"""TIKTOK FUNCTIONALITY"""

#on message
@client.on(CommentEvent)
async def on_comment(event: CommentEvent):
    username = event.user.nickname
    message = event.comment
    await MessageSort.msgSort(username, message, 'tiktok')

    
#when the bot connects
@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print('Connected!')


async def run_tiktok_bot():
    connected = False
    while True:
        try:
            if not connected:
                await client.start()
                connected = True
                print('connection happened!')
            else:
                await asyncio.sleep(10)
        except Exception as e:
            print("[TikTok] Stream is offline. Retrying in 10s...")
            print('[ERROR]:' + str(e))
            await asyncio.sleep(10)



"""TWITCH FUNCTIONALITY"""

async def on_message(msg: ChatMessage):
    username = msg.user.display_name
    message = msg.text
    await MessageSort.msgSort(username, message, 'twitch')
    
#bot connected successfully
async def on_ready(ready_event: EventData):
    #connect to TARGET_CHANNEL
    await ready_event.chat.join_room(TARGET_CHANNEL)

    #print ready message
    print('Bot Ready')


#guess command
async def on_guess(cmd: ChatCommand):
    await cmd.reply(cmd.text)


#lurk command
async def lurk_command(cmd: ChatCommand):
    chance = random.randint(0,4)

    name = cmd.user.display_name

    responses = [
        f"See you soon, {name}!",
        f"{name} is now lurking in the shadows 👀",
        f"Thanks for hanging out, {name}. Enjoy your lurk!",
        f"{name} just activated stealth mode 🕶️",
        f"Lurk mode engaged. Catch you later, {name}!"
    ]

    await cmd.reply(responses[chance])

#bot setupfunction
async def run_twitch_bot():
    bot = await Twitch(APP_ID, APP_SECRET)
    auth = UserAuthenticator(bot, USER_SCOPE)
    token, refresh_token = await auth.authenticate()
    await bot.set_user_authentication(token, USER_SCOPE, refresh_token)


    #initialize chat class
    chat = await Chat(bot)

    #register events
    chat.register_event(ChatEvent.READY, on_ready)
    chat.register_event(ChatEvent.MESSAGE, on_message)

    #register commands
    chat.register_command('lurk', lurk_command)

    #start the chatbot
    chat.start()
    

    try:
        while True:
            await asyncio.sleep(1)
    finally:
        chat.stop()
        await bot.close()


