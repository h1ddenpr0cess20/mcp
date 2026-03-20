class ConversationManager:
    def __init__(self):
        self._conversations = {}

    def get_history(self, conversation_id):
        """Get the message history for a conversation."""
        return list(self._conversations.get(conversation_id, []))

    def add_exchange(self, conversation_id, user_message, assistant_message):
        """Record a user/assistant exchange in a conversation."""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
        self._conversations[conversation_id].append(
            {"role": "user", "content": user_message}
        )
        self._conversations[conversation_id].append(
            {"role": "assistant", "content": assistant_message}
        )

    def list_conversations(self):
        """List all conversation IDs and their message counts."""
        return {
            cid: len(msgs) for cid, msgs in self._conversations.items()
        }

    def delete(self, conversation_id):
        """Delete a conversation. Returns True if it existed."""
        return self._conversations.pop(conversation_id, None) is not None
