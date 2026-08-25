class ConversationContext:
    def __init__(self,max_messages=20):
        self.messages=[]
        self.max_messages=max_messages

    def add(self,role,message):
        self.messages.append({
            "role":role,
            "message":message
        })

        if len(self.messages)>self.max_messages:
            self.messages.pop(0)

    def get_messages(self):
        return self.messages

    def last_message(self):
        if not self.messages:
            return None

        return self.messages[-1]