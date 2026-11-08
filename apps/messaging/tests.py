import tempfile

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from apps.community.models import Connection
from .models import Conversation, Message
from .services import get_connected_conversation
from .views import MAX_ATTACHMENT_SIZE

User=get_user_model()


class MessagingTests(TestCase):
    def setUp(self):
        self.media_temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.media_temp.cleanup)
        self.media_settings = override_settings(MEDIA_ROOT=self.media_temp.name)
        self.media_settings.enable()
        self.addCleanup(self.media_settings.disable)
        self.a = User.objects.create_user(
            email="a@example.com", password="StrongPass123!", first_name="A"
        )
        self.b = User.objects.create_user(
            email="b@example.com", password="StrongPass123!", first_name="B"
        )

    def connect_users(self):
        Connection.objects.create(sender=self.a, receiver=self.b, status="accepted")

    def start_conversation(self):
        self.connect_users()
        self.client.force_login(self.a)
        response = self.client.post(
            reverse("messaging:inbox"),
            {"user_id": self.b.pk},
        )
        conversation = Conversation.objects.get()
        self.assertEqual(get_connected_conversation(self.a, conversation.pk), conversation)
        self.assertRedirects(
            response,
            reverse("messaging:chat", args=[conversation.pk]),
            fetch_redirect_response=False,
        )
        return conversation

    def test_only_connected_users_can_start_conversation(self):
        self.client.force_login(self.a)
        self.client.post(reverse("messaging:inbox"), {"user_id": self.b.pk})
        self.assertEqual(Conversation.objects.count(), 0)

        self.connect_users()
        self.client.post(reverse("messaging:inbox"), {"user_id": self.b.pk})
        self.assertEqual(Conversation.objects.count(), 1)

    def test_connected_users_can_send_and_download_an_attachment(self):
        conversation = self.start_conversation()
        upload = SimpleUploadedFile(
            "study photo.png",
            b"\x89PNG\r\n\x1a\nsample-image",
            content_type="image/png",
        )

        response = self.client.post(
            reverse("messaging:send", args=[conversation.pk]),
            {"body": "Here is the diagram.", "attachment": upload},
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["is_own"])
        self.assertTrue(result["attachment_url"])
        message = Message.objects.get(conversation=conversation)
        self.assertEqual(message.attachment_name, "study photo.png")
        download = self.client.get(result["attachment_url"])
        self.addCleanup(download.close)
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/octet-stream")
        self.assertIn("attachment;", download["Content-Disposition"])
        self.client.force_login(self.b)
        incoming = self.client.get(reverse("messaging:poll", args=[conversation.pk]))
        self.assertEqual(incoming.status_code, 200)
        self.assertEqual(incoming.json()["messages"][0]["attachment_name"], "study photo.png")
        self.assertEqual(incoming.json()["messages"][0]["attachment_url"], result["attachment_url"])
        self.assertFalse(incoming.json()["messages"][0]["is_own"])

    def test_message_can_contain_only_an_attachment(self):
        conversation = self.start_conversation()
        upload = SimpleUploadedFile("notes.csv", b"id,value\n1,example\n")

        response = self.client.post(
            reverse("messaging:send", args=[conversation.pk]),
            {"body": "", "attachment": upload},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Message.objects.get().body, "")

    def test_message_must_contain_text_or_a_supported_file(self):
        conversation = self.start_conversation()

        empty_response = self.client.post(
            reverse("messaging:send", args=[conversation.pk]),
            {"body": ""},
        )
        unsupported_response = self.client.post(
            reverse("messaging:send", args=[conversation.pk]),
            {"body": "", "attachment": SimpleUploadedFile("run.exe", b"no")},
        )

        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(unsupported_response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_attachment_size_is_limited(self):
        conversation = self.start_conversation()
        upload = SimpleUploadedFile(
            "large.pdf",
            b"x" * (MAX_ATTACHMENT_SIZE + 1),
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("messaging:send", args=[conversation.pk]),
            {"body": "", "attachment": upload},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_attachment_download_is_private_to_connected_conversation_members(self):
        conversation = self.start_conversation()
        response = self.client.post(
            reverse("messaging:send", args=[conversation.pk]),
            {
                "body": "",
                "attachment": SimpleUploadedFile("notes.txt", b"private note"),
            },
        )
        message_id = response.json()["id"]

        self.client.force_login(self.b)
        download = self.client.get(reverse("messaging:download", args=[message_id]))
        self.addCleanup(download.close)
        self.assertEqual(
            download.status_code,
            200,
        )
        self.client.force_login(User.objects.create_user(
            email="stranger@example.com", password="StrongPass123!"
        ))
        self.assertEqual(
            self.client.get(reverse("messaging:download", args=[message_id])).status_code,
            404,
        )

    def test_community_chat_is_only_available_to_accepted_connections(self):
        self.client.force_login(self.a)

        self.assertEqual(
            self.client.get(reverse("community:chat", args=[self.b.pk])).status_code,
            404,
        )
        self.connect_users()
        response = self.client.get(reverse("community:chat", args=[self.b.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Attach photo or file")
        self.assertEqual(Conversation.objects.count(), 1)
        home = self.client.get(reverse("community:home"))
        self.assertContains(home, reverse("community:chat", args=[self.b.pk]))

    def test_conversation_access_is_revoked_when_connection_is_no_longer_accepted(self):
        conversation = self.start_conversation()
        Connection.objects.update(status="declined")

        self.assertEqual(
            self.client.get(reverse("messaging:chat", args=[conversation.pk])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("messaging:poll", args=[conversation.pk])).status_code,
            404,
        )
