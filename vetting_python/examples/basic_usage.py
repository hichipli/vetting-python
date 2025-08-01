"""
Basic usage examples for the VETTING framework.

This module demonstrates the most common usage patterns for getting started
with the VETTING framework for both chat and vetting modes.
"""

import asyncio
import os
from typing import List

# Import VETTING framework components
from vetting_python import (
    VettingFramework, VettingConfig, ChatMessage,
    OpenAIProvider, ClaudeProvider, GeminiProvider
)
from vetting_python.config import VettingSettings, VettingConfigBuilder
from vetting_python.utils import CostTracker


async def basic_chat_example():
    """Basic example of using VETTING framework in chat mode."""
    print("=== Basic Chat Example ===")
    
    # Setup provider (OpenAI in this case)
    provider = OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
    )
    
    # Create framework instance
    framework = VettingFramework(chat_provider=provider)
    
    # Create simple chat configuration
    config = VettingConfig(
        mode="chat",
        chat_model={"model_id": "gpt-4o-mini", "temperature": 0.7, "max_tokens": 200}
    )
    
    # Create conversation
    messages = [
        ChatMessage("user", "Hello! Can you help me understand what photosynthesis is?")
    ]
    
    # Process the conversation
    try:
        response = await framework.process(messages, config)
        
        print(f"Response: {response.content}")
        print(f"Tokens used: {response.total_usage.total_tokens}")
        print(f"Cost: ${response.total_cost:.4f}")
        print(f"Safety attention required: {response.requires_attention}")
        
    except Exception as e:
        print(f"Error: {e}")


async def basic_vetting_example():
    """Basic example of using VETTING framework in vetting mode."""
    print("\n=== Basic Vetting Example ===")
    
    # Setup provider
    provider = OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
    )
    
    # Create framework instance
    framework = VettingFramework(
        chat_provider=provider,
        verification_provider=provider  # Same provider for both layers
    )
    
    # Create vetting configuration using the builder
    config = (VettingConfigBuilder()
              .vetting_mode()
              .chat_model("gpt-4o-mini", temperature=0.7, max_tokens=300)
              .verification_model("gpt-4o-mini", temperature=0.1, max_tokens=100)
              .max_attempts(3)
              .add_context_item(
                  question_text="What is the capital of France?",
                  question_id="geo_001",
                  correct_answer="Paris",
                  key_concepts=["Paris", "France", "capital city"],
                  explanation="Paris is the capital and largest city of France."
              )
              .build())
    
    # Create conversation
    messages = [
        ChatMessage("user", "I have a geography question. What is the capital of France?")
    ]
    
    # Process with verification
    try:
        response = await framework.process(messages, config)
        
        print(f"Response: {response.content}")
        print(f"Verification passed: {response.verification_passed}")
        print(f"Attempts made: {response.attempt_count}")
        print(f"Stop reason: {response.stop_reason}")
        print(f"Total tokens: {response.total_usage.total_tokens}")
        print(f"Total cost: ${response.total_cost:.4f}")
        
    except Exception as e:
        print(f"Error: {e}")


async def multi_provider_example():
    """Example using different providers for chat and verification."""
    print("\n=== Multi-Provider Example ===")
    
    # Setup different providers
    chat_provider = OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY", "your-openai-key")
    )
    
    verification_provider = ClaudeProvider(
        api_key=os.getenv("ANTHROPIC_API_KEY", "your-claude-key")
    )
    
    # Create framework with different providers
    framework = VettingFramework(
        chat_provider=chat_provider,
        verification_provider=verification_provider
    )
    
    # Create configuration
    config = VettingConfig(
        mode="vetting",
        chat_model={"model_id": "gpt-4o-mini", "temperature": 0.8},
        verification_model={"model_id": "claude-3-haiku", "temperature": 0.1},
        max_attempts=2
    )
    
    messages = [
        ChatMessage("user", "Can you explain quantum mechanics in simple terms?")
    ]
    
    try:
        response = await framework.process(messages, config)
        print(f"Used different providers - Chat: OpenAI, Verification: Claude")
        print(f"Response: {response.content[:200]}...")  # First 200 chars
        print(f"Verification: {'✓' if response.verification_passed else '✗'}")
        
    except Exception as e:
        print(f"Error: {e}")


async def educational_vetting_example():
    """Example of educational vetting with multiple questions."""
    print("\n=== Educational Vetting Example ===")
    
    provider = OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
    )
    
    framework = VettingFramework(chat_provider=provider)
    
    # Educational configuration with multiple context items
    config = (VettingConfigBuilder()
              .vetting_mode()
              .chat_model("gpt-4o-mini", temperature=0.7)
              .verification_model("gpt-4o-mini", temperature=0.1)
              .chat_system_prompt(
                  "You are an educational tutor. Help students learn by asking "
                  "guiding questions rather than giving direct answers. Encourage "
                  "critical thinking and discovery."
              )
              .add_context_item(
                  question_text="What is the process by which plants make their own food?",
                  subject="Biology",
                  correct_answer="Photosynthesis",
                  key_concepts=["photosynthesis", "chlorophyll", "sunlight", "carbon dioxide", "glucose"],
                  explanation="Photosynthesis is the process where plants convert light energy into chemical energy."
              )
              .add_context_item(
                  question_text="What gas do plants absorb during photosynthesis?",
                  subject="Biology", 
                  correct_answer="Carbon dioxide",
                  key_concepts=["carbon dioxide", "CO2"],
                  explanation="Plants absorb CO2 from the atmosphere during photosynthesis."
              )
              .safety_features(enable_educational_rules=True)
              .session_info(session_id="edu_session_001", user_id="student_123")
              .build())
    
    # Student asks a direct question
    messages = [
        ChatMessage("user", "What is photosynthesis? I need the answer for my homework.")
    ]
    
    try:
        response = await framework.process(messages, config)
        
        print("Educational Response:")
        print(f"Content: {response.content}")
        print(f"Verification passed: {response.verification_passed}")
        print(f"Session ID: {response.session_id}")
        
        # Show verification attempts
        if response.attempts:
            print(f"\nVerification Details:")
            for attempt in response.attempts:
                status = "✓ PASS" if attempt.verification_passed else "✗ FAIL"
                print(f"  Attempt {attempt.attempt_number}: {status}")
                if not attempt.verification_passed:
                    print(f"    Reason: {attempt.verification_output}")
        
    except Exception as e:
        print(f"Error: {e}")


async def cost_tracking_example():
    """Example of using cost tracking with the framework."""
    print("\n=== Cost Tracking Example ===")
    
    # Setup cost tracker
    cost_tracker = CostTracker(enable_persistence=True)
    
    provider = OpenAIProvider(
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
    )
    
    framework = VettingFramework(chat_provider=provider)
    
    # Multiple requests with cost tracking
    configs_and_messages = [
        (
            VettingConfig(mode="chat", chat_model={"model_id": "gpt-4o-mini"}),
            [ChatMessage("user", "What's the weather like?")]
        ),
        (
            VettingConfig(mode="chat", chat_model={"model_id": "gpt-4o"}),
            [ChatMessage("user", "Explain machine learning.")]
        ),
        (
            (VettingConfigBuilder()
             .vetting_mode()
             .chat_model("gpt-4o-mini")
             .add_context_item("What is AI?", correct_answer="Artificial Intelligence")
             .build()),
            [ChatMessage("user", "What does AI stand for?")]
        )
    ]
    
    print("Making multiple requests with cost tracking...")
    
    for i, (config, messages) in enumerate(configs_and_messages, 1):
        try:
            response = await framework.process(messages, config)
            
            # Track the response
            cost_tracker.track_response(response, "openai", provider, provider)
            
            print(f"Request {i}: ${response.total_cost:.4f} ({response.total_usage.total_tokens} tokens)")
            
        except Exception as e:
            print(f"Request {i} failed: {e}")
    
    # Print cost summary
    print("\n--- Cost Summary ---")
    cost_tracker.print_summary()


async def settings_based_example():
    """Example using VettingSettings for configuration management."""
    print("\n=== Settings-Based Configuration Example ===")
    
    # Load settings from environment
    settings = VettingSettings.from_env()
    
    # Validate settings
    if not settings.validate():
        print("Settings validation failed. Please check your API keys and configuration.")
        return
    
    # Get provider instance
    try:
        provider = settings.get_provider_instance("openai")
    except Exception as e:
        print(f"Could not create provider: {e}")
        return
    
    # Create framework
    framework = VettingFramework(chat_provider=provider)
    
    # Create default configuration
    config = settings.create_default_vetting_config(mode="chat")
    
    messages = [
        ChatMessage("user", "Hello! Tell me about the VETTING framework.")
    ]
    
    try:
        response = await framework.process(messages, config)
        print(f"Response using settings: {response.content[:150]}...")
        print(f"Model used: {response.chat_model_used}")
        
    except Exception as e:
        print(f"Error: {e}")


def print_example_info():
    """Print information about running these examples."""
    print("VETTING Framework Examples")
    print("=" * 50)
    print("To run these examples, you need to set environment variables:")
    print("  OPENAI_API_KEY=your_openai_api_key")
    print("  ANTHROPIC_API_KEY=your_claude_api_key (optional)")
    print("  GOOGLE_API_KEY=your_gemini_api_key (optional)")
    print()
    print("You can also create a .env file with these variables.")
    print("=" * 50)


async def main():
    """Run all examples."""
    print_example_info()
    
    # Check if we have at least OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Some examples may fail.")
        print("Please set your API key to run these examples properly.")
        return
    
    # Run examples
    await basic_chat_example()
    await basic_vetting_example()
    
    # Only run multi-provider if we have both keys
    if os.getenv("ANTHROPIC_API_KEY"):
        await multi_provider_example()
    else:
        print("\n=== Multi-Provider Example === (Skipped - no Claude API key)")
        
    await educational_vetting_example()
    await cost_tracking_example()
    await settings_based_example()
    
    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    # For direct execution
    asyncio.run(main())