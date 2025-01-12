"""
Slack webhook integration for Agent360.
"""

from typing import Dict, Any, List, Optional, Union
from .base import BaseIntegration

class SlackIntegration(BaseIntegration):
    """Integration with Slack webhooks."""
    
    def __init__(self, webhook_url: str):
        """Initialize Slack integration.
        
        Args:
            webhook_url: Slack webhook URL
        """
        super().__init__("")  # No API token needed for webhooks
        self.webhook_url = webhook_url
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get Slack headers."""
        return {
            "Content-Type": "application/json"
        }
    
    async def health_check(self) -> bool:
        """Check if Slack webhook is accessible."""
        try:
            # Send a test message that's only visible to the sender
            await self.send_message(
                "Test message",
                channel="@test",
                ephemeral=True
            )
            return True
        except Exception:
            return False
    
    async def send_message(
        self,
        text: str,
        channel: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        thread_ts: Optional[str] = None,
        ephemeral: bool = False
    ) -> Dict[str, Any]:
        """Send a message to Slack.
        
        Args:
            text: Message text
            channel: Optional channel or user to send to
            blocks: Optional block kit blocks
            attachments: Optional message attachments
            thread_ts: Optional thread timestamp to reply to
            ephemeral: Whether the message should be ephemeral
            
        Returns:
            Response data
        """
        data: Dict[str, Any] = {"text": text}
        
        if channel:
            data["channel"] = channel
        if blocks:
            data["blocks"] = blocks
        if attachments:
            data["attachments"] = attachments
        if thread_ts:
            data["thread_ts"] = thread_ts
        if ephemeral:
            data["ephemeral"] = True
        
        return await self._make_request(
            "POST",
            self.webhook_url,
            data=data
        )
    
    async def send_notification(
        self,
        title: str,
        message: str,
        severity: str = "info",
        fields: Optional[List[Dict[str, str]]] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a formatted notification.
        
        Args:
            title: Notification title
            message: Notification message
            severity: Severity level (info, warning, error)
            fields: Optional additional fields
            channel: Optional channel to send to
            
        Returns:
            Response data
        """
        color_map = {
            "info": "#36a64f",
            "warning": "#ffcc00",
            "error": "#ff0000"
        }
        
        attachment = {
            "color": color_map.get(severity, "#36a64f"),
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message
                    }
                }
            ]
        }
        
        if fields:
            attachment["blocks"].append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*{field['title']}*\n{field['value']}"
                    }
                    for field in fields
                ]
            })
        
        return await self.send_message(
            text=title,
            channel=channel,
            attachments=[attachment]
        )
    
    async def send_error_alert(
        self,
        error: Union[str, Exception],
        context: Optional[Dict[str, Any]] = None,
        channel: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send an error alert.
        
        Args:
            error: Error message or exception
            context: Optional error context
            channel: Optional channel to send to
            
        Returns:
            Response data
        """
        error_message = str(error)
        fields = []
        
        if context:
            fields.extend([
                {"title": key, "value": str(value)}
                for key, value in context.items()
            ])
        
        return await self.send_notification(
            title="⚠️ Error Alert",
            message=f"```{error_message}```",
            severity="error",
            fields=fields,
            channel=channel
        )
