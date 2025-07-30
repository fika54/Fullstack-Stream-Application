import app.Chat_Manager as Chat_Manager

"""FILE Variables"""

SESSION_ID = ""

"""COMMAND CENTER"""
#sorts incoming chat messages
async def msgSort(username, message: str, chat):
    print(f"Received message from {username} on {chat}: {message}")
    if message.lower() == "..player1":
        print(f"Adding {username} to Character 1 pool.")
        Chat_Manager.CHARACTER_POOL_1.add_chatter(username, chat)
    elif message.lower() == "..player2":
        Chat_Manager.CHARACTER_POOL_2.add_chatter(username, chat)
    
    Chat_Manager.handle_chatter_message(username, chat, message)

