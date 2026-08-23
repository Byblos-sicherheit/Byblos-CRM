import unittest

from byblos_agent.contracts import ContractError, validate_chat_request


class ContractTests(unittest.TestCase):
    def test_accepts_valid_request(self):
        request = validate_chat_request(
            {
                "conversationId": "conversation-1",
                "messages": [{"role": "user", "content": "Hallo"}],
            }
        )
        self.assertEqual(request.conversation_id, "conversation-1")
        self.assertEqual(request.messages[0].content, "Hallo")

    def test_requires_last_message_to_be_user(self):
        with self.assertRaises(ContractError) as raised:
            validate_chat_request(
                {
                    "conversationId": "conversation-1",
                    "messages": [{"role": "assistant", "content": "Hallo"}],
                }
            )
        self.assertEqual(raised.exception.code, "invalid_request")

    def test_rejects_oversized_message(self):
        with self.assertRaises(ContractError):
            validate_chat_request(
                {
                    "conversationId": "conversation-1",
                    "messages": [{"role": "user", "content": "x" * 8001}],
                }
            )


if __name__ == "__main__":
    unittest.main()
