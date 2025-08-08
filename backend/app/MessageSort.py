import app.Chat_Manager as Chat_Manager
import app.functions.poll_manager as Poll_Manager

"""FILE Variables"""

SESSION_ID = ""

"""COMMAND CENTER"""
#sorts incoming chat messages
async def msgSort(username, message: str, chat):
    try:
        print(f"Received message from {username} on {chat}: {message}")
        if message.lower().startswith("..player") :
            player_number = message.replace("..player", "").strip()
            if player_number.isdigit():
                num = int(player_number)
                Chat_Manager.add_chatter_to_character_pool(num, username, chat)
                print(f"Adding {username} to Character {num} pool.")

        if Poll_Manager.is_valid_vote(message):
            success, response = await Poll_Manager.handle_vote(message.strip())
            if success:
                print(f"Vote counted: {response}")
            else:
                print(f"Vote error: {response}")
                
        Chat_Manager.handle_chatter_message(username, chat, message)

        if message == "start":
            await Poll_Manager.start_poll()
            print("Poll started.")


        if message == "end":
            await Poll_Manager.end_poll()
            print("Poll ended.")

        if message == "hide":
            await Poll_Manager.hide_poll()
            print("Poll hidden.")
    except Exception as e:
        print(f"[ERROR] Failed to sort message: {e}")
    
    

