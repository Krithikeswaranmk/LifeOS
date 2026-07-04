import requests
BOT_TOKEN = "8780480300:AAHyXNHGLJY3rVXAeJj42zEwWNWrljjF5fQ"
resp = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates")
updates = resp.json()['result']
if updates:
    chat_id = updates[-1]['message']['chat']['id']
    print(f"Your correct chat ID is: {chat_id}")