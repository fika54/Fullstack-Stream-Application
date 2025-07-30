import app.Chat_Manager as Chat_Manager

"""FILE Variables"""

SESSION_ID = ""

"""COMMAND CENTER"""
#sorts incoming chat messages
async def msgSort(username, message: str, chat):
    if message.lower == "..player1":
        Chat_Manager.CHARACTER_POOL_1.add_chatter(username, chat)
    elif message.lower() == "..player2":
        Chat_Manager.CHARACTER_POOL_2.add_chatter(username, chat)
    
    Chat_Manager.handle_chatter_message(username, chat, message)

