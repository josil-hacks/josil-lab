import asyncio
import os
import smtplib
import ssl
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from pydantic import ValidationError
from contact_form.main import ContactSchema, Settings, allowed_origins, app, lifespan, load_settings, send_email


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.password_file = Path(self.temp.name) / 'password'
        self.password_file.write_text('test password\n')
        self.env = {'SMTP_SERVER': 'smtp.example.com', 'SMTP_PORT': '587',
                    'SENDER_EMAIL': 'sender@example.com', 'RECEIVER_EMAIL': 'recipient@example.com',
                    'SMTP_PASSWORD_FILE': str(self.password_file)}

    def test_password_file_and_defaults(self):
        del self.env['SMTP_PORT']
        with patch.dict(os.environ, self.env, clear=True):
            settings = load_settings()
        self.assertEqual(settings.password, 'test password')
        self.assertEqual(settings.smtp_port, 587)
        self.assertNotIn('test password', repr(settings))

    def test_missing_invalid_and_unreadable_configuration(self):
        for key, value, expected in [('SMTP_SERVER', '', 'SMTP_SERVER'), ('SMTP_PORT', '0', 'SMTP_PORT'),
                                      ('SENDER_EMAIL', 'bad', 'SENDER_EMAIL'),
                                      ('SMTP_PASSWORD_FILE', '/missing/file', 'SMTP_PASSWORD_FILE')]:
            with self.subTest(key=key), patch.dict(os.environ, {**self.env, key: value}, clear=True):
                with self.assertRaisesRegex(ValueError, expected):
                    load_settings()
        self.password_file.write_text('\n')
        with patch.dict(os.environ, self.env, clear=True), self.assertRaisesRegex(ValueError, 'non-empty'):
            load_settings()

    def test_lifespan_loads_settings_and_fails_on_missing_configuration(self):
        async def start():
            async with lifespan(app):
                self.assertEqual(app.state.settings.password, 'test password')
        with patch.dict(os.environ, self.env, clear=True):
            asyncio.run(start())
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, 'SMTP_SERVER'):
            asyncio.run(start())

    def test_cors_requires_explicit_origins(self):
        with patch.dict(os.environ, {'CORS_ORIGINS': 'https://example.com, https://site.example:8443'}, clear=True):
            self.assertEqual(len(allowed_origins()), 2)
        for value in ('*', 'https://example.com/path', 'https://example.com:bad'):
            with self.subTest(value=value), patch.dict(os.environ, {'CORS_ORIGINS': value}, clear=True):
                with self.assertRaises(ValueError):
                    allowed_origins()


class ContactTests(unittest.TestCase):
    def test_validation(self):
        for changes in ({'name': ' \r\n '}, {'message': ' \n '}, {'email': 'invalid'},
                        {'name': 'x' * 101}, {'message': 'x' * 5001}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ContactSchema(**({'name': 'Alice', 'email': 'alice@example.com', 'message': 'Hello'} | changes))
        self.assertEqual(ContactSchema(name='Alice\r\nBcc: test', email='alice@example.com', message='Hi').name,
                         'Alice  Bcc: test')

    def test_dispatch_and_failure_close_connection(self):
        contact = ContactSchema(name='Alice', email='alice@example.com', message='Private content')
        settings = Settings('smtp.example.com', 587, 'sender@example.com', 'recipient@example.com', 'secret')
        connection = MagicMock()
        connection.__enter__.return_value = connection
        with patch('contact_form.main.smtplib.SMTP', return_value=connection) as smtp:
            self.assertTrue(send_email(contact, settings))
            smtp.assert_called_once_with('smtp.example.com', 587, timeout=10)
            self.assertIsInstance(connection.starttls.call_args.kwargs['context'], ssl.SSLContext)
            connection.login.assert_called_once_with('sender@example.com', 'secret')
            msg = connection.send_message.call_args.args[0]
            self.assertEqual(msg['From'], 'sender@example.com')
            self.assertEqual(msg['To'], 'recipient@example.com')
            self.assertEqual(msg['Reply-To'], 'alice@example.com')
            self.assertIn('Private content', msg.get_content())
            connection.__exit__.assert_called_once()
        connection.reset_mock()
        connection.login.side_effect = smtplib.SMTPException('secret Private content')
        with patch('contact_form.main.smtplib.SMTP', return_value=connection), self.assertLogs('contact_form.main') as logs:
            self.assertFalse(send_email(contact, settings))
        connection.__exit__.assert_called_once()
        self.assertNotIn('secret', str(logs.output))
        self.assertNotIn('Private content', str(logs.output))


if __name__ == '__main__':
    unittest.main()
