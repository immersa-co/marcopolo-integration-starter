import unittest

from backend.app.services.auth.service import (
    _normalized_auth_payload_for_mode,
    user_session_from_auth_payload,
)


class AuthSessionContractTests(unittest.TestCase):
    def test_switching_auth_mode_clears_marcopolo_auth_state(self) -> None:
        payload = _normalized_auth_payload_for_mode(
            {
                "provider": "demo_session",
                "user": {
                    "subject": "demo_session:partner@example.com",
                    "email": "partner@example.com",
                },
                "marcopolo_access_token": "stale-access-token",
                "marcopolo_provisioned": True,
                "company": "entelligence-demo",
                "namespace": "entelligence",
            },
            "developer_api_token",
        )

        session = user_session_from_auth_payload(payload)

        self.assertEqual(session.marcopolo_auth_mode, "developer_api_token")
        self.assertFalse(session.marcopolo_provisioned)
        self.assertIsNone(session.marcopolo_access_token)
        self.assertIsNone(session.company)
        self.assertIsNone(session.namespace)


if __name__ == "__main__":
    unittest.main()
