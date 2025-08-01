"""
Message utilities for the VETTING framework.

This module provides utility functions for working with chat messages,
including formatting, conversion, and manipulation.
"""

from typing import List, Dict, Any, Optional, Union
from ..core.models import ChatMessage


class MessageUtils:
    """Utility functions for working with chat messages."""
    
    @staticmethod
    def from_openai_format(messages: List[Dict[str, str]]) -> List[ChatMessage]:
        """
        Convert OpenAI-style messages to ChatMessage objects.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            
        Returns:
            List of ChatMessage objects
        """
        return [
            ChatMessage(
                role=msg["role"],
                content=msg["content"],
                metadata=msg.get("metadata")
            )
            for msg in messages
        ]
    
    @staticmethod
    def to_openai_format(messages: List[ChatMessage]) -> List[Dict[str, str]]:
        """
        Convert ChatMessage objects to OpenAI-style format.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in messages]
    
    @staticmethod
    def create_conversation(
        user_messages: List[str],
        assistant_messages: Optional[List[str]] = None,
        system_prompt: Optional[str] = None
    ) -> List[ChatMessage]:
        """
        Create a conversation from separate user and assistant message lists.
        
        Args:
            user_messages: List of user message strings
            assistant_messages: Optional list of assistant responses
            system_prompt: Optional system prompt to add at the beginning
            
        Returns:
            List of ChatMessage objects forming a conversation
        """
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append(ChatMessage("system", system_prompt))
        
        # Interleave user and assistant messages
        assistant_messages = assistant_messages or []
        
        for i, user_msg in enumerate(user_messages):
            messages.append(ChatMessage("user", user_msg))
            
            # Add assistant response if available
            if i < len(assistant_messages):
                messages.append(ChatMessage("assistant", assistant_messages[i]))
        
        return messages
    
    @staticmethod
    def extract_system_prompt(messages: List[ChatMessage]) -> Optional[str]:
        """
        Extract the system prompt from a list of messages.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            System prompt content if found, None otherwise
        """
        for msg in messages:
            if msg.role == "system":
                return msg.content
        return None
    
    @staticmethod
    def remove_system_messages(messages: List[ChatMessage]) -> List[ChatMessage]:
        """
        Remove all system messages from a conversation.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            List with system messages removed
        """
        return [msg for msg in messages if msg.role != "system"]
    
    @staticmethod
    def count_tokens_estimate(messages: List[ChatMessage]) -> int:
        """
        Rough estimate of token count for messages.
        
        Uses a simple heuristic: ~4 characters per token.
        For more accurate counting, use the specific provider's tokenizer.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg.content) for msg in messages)
        return int(total_chars / 4)  # Rough estimate
    
    @staticmethod
    def truncate_conversation(
        messages: List[ChatMessage],
        max_tokens: int,
        preserve_system: bool = True
    ) -> List[ChatMessage]:
        """
        Truncate conversation to fit within token limit.
        
        Removes oldest messages first, optionally preserving system messages.
        
        Args:
            messages: List of ChatMessage objects
            max_tokens: Maximum token limit
            preserve_system: Whether to preserve system messages
            
        Returns:
            Truncated list of messages
        """
        # Separate system and other messages
        system_messages = [msg for msg in messages if msg.role == "system"]
        other_messages = [msg for msg in messages if msg.role != "system"]
        
        # Start with system messages if preserving them
        result = system_messages if preserve_system else []
        current_tokens = MessageUtils.count_tokens_estimate(result)
        
        # Add other messages from most recent backwards
        for msg in reversed(other_messages):
            msg_tokens = MessageUtils.count_tokens_estimate([msg])
            if current_tokens + msg_tokens <= max_tokens:
                result.insert(-len(system_messages) if preserve_system else 0, msg)
                current_tokens += msg_tokens
            else:
                break
        
        return result
    
    @staticmethod
    def format_conversation_for_display(
        messages: List[ChatMessage],
        include_metadata: bool = False
    ) -> str:
        """
        Format conversation for human-readable display.
        
        Args:
            messages: List of ChatMessage objects
            include_metadata: Whether to include metadata in output
            
        Returns:
            Formatted conversation string
        """
        lines = []
        
        for i, msg in enumerate(messages):
            role_display = {
                "system": "🔧 System",
                "user": "👤 User",
                "assistant": "🤖 Assistant"
            }.get(msg.role, f"❓ {msg.role.title()}")
            
            lines.append(f"{role_display}:")
            lines.append(msg.content)
            
            if include_metadata and msg.metadata:
                lines.append(f"   Metadata: {msg.metadata}")
            
            if i < len(messages) - 1:
                lines.append("")  # Empty line between messages
        
        return "\n".join(lines)
    
    @staticmethod
    def get_conversation_stats(messages: List[ChatMessage]) -> Dict[str, Any]:
        """
        Get statistics about a conversation.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            Dictionary with conversation statistics
        """
        role_counts = {"system": 0, "user": 0, "assistant": 0}
        total_chars = 0
        total_words = 0
        
        for msg in messages:
            role_counts[msg.role] = role_counts.get(msg.role, 0) + 1
            total_chars += len(msg.content)
            total_words += len(msg.content.split())
        
        return {
            "total_messages": len(messages),
            "role_breakdown": role_counts,
            "total_characters": total_chars,
            "total_words": total_words,
            "estimated_tokens": MessageUtils.count_tokens_estimate(messages),
            "average_message_length": total_chars / len(messages) if messages else 0
        }
    
    @staticmethod
    def validate_conversation(messages: List[ChatMessage]) -> Dict[str, Any]:
        """
        Validate a conversation for common issues.
        
        Args:
            messages: List of ChatMessage objects
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        
        if not messages:
            issues.append("Conversation is empty")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        # Check for consecutive messages from same role
        for i in range(1, len(messages)):
            if messages[i].role == messages[i-1].role and messages[i].role != "system":
                warnings.append(f"Consecutive {messages[i].role} messages at positions {i-1}, {i}")
        
        # Check if conversation starts with user message (after system)
        non_system_messages = [msg for msg in messages if msg.role != "system"]
        if non_system_messages and non_system_messages[0].role != "user":
            warnings.append("Conversation should typically start with a user message")
        
        # Check for empty messages
        for i, msg in enumerate(messages):
            if not msg.content.strip():
                issues.append(f"Empty message at position {i}")
        
        # Check for extremely long messages
        for i, msg in enumerate(messages):
            if len(msg.content) > 8000:  # Rough limit for most models
                warnings.append(f"Very long message at position {i} ({len(msg.content)} chars)")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings
        }