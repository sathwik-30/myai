from backend.brain.conversation import ConversationEngine

medha=ConversationEngine()

while True:
    message=input("You: ")

    if message.lower()=="exit":
        break

    response=medha.chat(message)

    print("Medha:",response)