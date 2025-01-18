"""
Tests for Slack integration.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.integrations.slack import SlackIntegration

@pytest.fixture
def slack():
    return SlackIntegration("https://hooks.slack.com/services/TEST/TEST/test")

@pytest.mark.asyncio
async def test_send_message(slack):
    with patch.object(slack, '_make_request') as mock_request:
        mock_request.return_value = {"ok": True}
        
        result = await slack.send_message(
            text="Test Message",
            channel="#test",
            blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
            thread_ts="1234567890.123456"
        )
        
        mock_request.assert_called_once_with(
            "POST",
            slack.webhook_url,
            data={
                "text": "Test Message",
                "channel": "#test",
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
                "thread_ts": "1234567890.123456"
            }
        )
        assert result["ok"] is True

@pytest.mark.asyncio
async def test_send_notification(slack):
    with patch.object(slack, 'send_message') as mock_send:
        mock_send.return_value = {"ok": True}
        
        fields = [
            {"title": "Priority", "value": "High"},
            {"title": "Status", "value": "Active"}
        ]
        
        result = await slack.send_notification(
            title="Test Alert",
            message="Something happened",
            severity="warning",
            fields=fields,
            channel="#alerts"
        )
        
        mock_send.assert_called_once()
        call_args = mock_send.call_args[1]
        
        assert call_args["text"] == "Test Alert"
        assert call_args["channel"] == "#alerts"
        assert len(call_args["attachments"]) == 1
        
        attachment = call_args["attachments"][0]
        assert attachment["color"] == "#ffcc00"  # warning color
        assert len(attachment["blocks"]) == 3  # header, message, fields
        
        assert result["ok"] is True

@pytest.mark.asyncio
async def test_send_error_alert(slack):
    with patch.object(slack, 'send_notification') as mock_notify:
        mock_notify.return_value = {"ok": True}
        
        context = {
            "service": "test-service",
            "environment": "production"
        }
        
        result = await slack.send_error_alert(
            error="Test Error",
            context=context,
            channel="#errors"
        )
        
        mock_notify.assert_called_once_with(
            title="⚠️ Error Alert",
            message="```Test Error```",
            severity="error",
            fields=[
                {"title": "service", "value": "test-service"},
                {"title": "environment", "value": "production"}
            ],
            channel="#errors"
        )
        
        assert result["ok"] is True

@pytest.mark.asyncio
async def test_health_check_success(slack):
    with patch.object(slack, 'send_message') as mock_send:
        mock_send.return_value = {"ok": True}
        result = await slack.health_check()
        assert result is True
        mock_send.assert_called_once()

@pytest.mark.asyncio
async def test_health_check_failure(slack):
    with patch.object(slack, 'send_message') as mock_send:
        mock_send.side_effect = Exception("Webhook Error")
        result = await slack.health_check()
        assert result is False
