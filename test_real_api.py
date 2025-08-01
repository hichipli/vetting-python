#!/usr/bin/env python3
"""
Real API test script for VETTING framework.

This script tests the actual functionality with OpenAI API.
"""

import asyncio
import os
import sys
import traceback
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from vetting_python import VettingFramework, VettingConfig, ChatMessage, ModelConfig, OpenAIProvider
from vetting_python.core.models import ContextItem


async def test_chat_mode():
    """Test basic chat mode functionality."""
    print("=" * 50)
    print("Testing Chat Mode")
    print("=" * 50)
    
    try:
        # Initialize provider with API key
        provider = OpenAIProvider(api_key="INSERT_OPENAI_API_KEY_HERE")
        framework = VettingFramework(chat_provider=provider)
        
        # Create config
        config = VettingConfig(
            mode="chat",
            chat_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.7, max_tokens=100)
        )
        
        # Test simple chat
        messages = [ChatMessage("user", "Hello! Can you tell me what 2+2 equals?")]
        response = await framework.process(messages, config)
        
        print(f"✅ Chat Response: {response.content}")
        print(f"✅ Total Cost: ${response.total_cost:.6f}")
        if response.total_usage:
            print(f"✅ Token Usage: {response.total_usage.total_tokens} tokens")
        else:
            print(f"✅ Token Usage: No usage data available")
        print(f"✅ Requires Attention: {response.requires_attention}")
        
        return True
        
    except Exception as e:
        print(f"❌ Chat Mode Test Failed: {e}")
        traceback.print_exc()
        return False


async def test_vetting_mode():
    """Test vetting mode functionality."""
    print("\n" + "=" * 50)
    print("Testing Vetting Mode")
    print("=" * 50)
    
    try:
        # Initialize provider
        provider = OpenAIProvider(api_key="INSERT_OPENAI_API_KEY_HERE")
        framework = VettingFramework(chat_provider=provider)
        
        # Create educational context
        context_item = ContextItem(
            question={
                "text": "What is 2 + 2?",
                "id": "math_basic_001", 
                "subject": "Elementary Math"
            },
            answer_key={
                "correctAnswer": "4",
                "keyConcepts": ["addition", "arithmetic"],
                "explanation": "Adding 2 and 2 gives us 4."
            }
        )
        
        # Create vetting config
        config = VettingConfig(
            mode="vetting",
            chat_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.7, max_tokens=150),
            verification_model=ModelConfig(model_id="gpt-4o-mini", temperature=0.1, max_tokens=100),
            context_items=[context_item],
            max_attempts=2,
            enable_educational_rules=True,
            enable_safety_prefix=True
        )
        
        # Test vetting with educational question
        messages = [ChatMessage("user", "I need help with my math homework. What is 2 + 2?")]
        response = await framework.process(messages, config)
        
        print(f"✅ Vetting Response: {response.content}")
        print(f"✅ Verification Passed: {response.verification_passed}")
        print(f"✅ Attempt Count: {response.attempt_count}")
        print(f"✅ Stop Reason: {response.stop_reason}")
        print(f"✅ Total Cost: ${response.total_cost:.6f}")
        if response.total_usage:
            print(f"✅ Total Token Usage: {response.total_usage.total_tokens} tokens")
        else:
            print(f"✅ Total Token Usage: No usage data available")
        
        if response.attempts:
            print(f"✅ Detailed Attempts:")
            for i, attempt in enumerate(response.attempts, 1):
                print(f"   Attempt {i}: Verification {'PASSED' if attempt.verification_passed else 'FAILED'}")
                if not attempt.verification_passed:
                    print(f"   Reason: {attempt.verification_output}")
        
        return True
        
    except Exception as e:
        print(f"❌ Vetting Mode Test Failed: {e}")
        traceback.print_exc()
        return False


async def test_cost_calculation():
    """Test cost calculation accuracy."""
    print("\n" + "=" * 50)
    print("Testing Cost Calculation")
    print("=" * 50)
    
    try:
        provider = OpenAIProvider(api_key="INSERT_OPENAI_API_KEY_HERE")
        
        # Test model pricing info
        supported_models = provider.get_supported_models()
        print(f"✅ Supported Models: {supported_models[:5]}...")  # Show first 5
        
        aliases = provider.get_model_aliases()
        print(f"✅ Model Aliases: {aliases}")
        
        return True
        
    except Exception as e:
        print(f"❌ Cost Calculation Test Failed: {e}")
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("VETTING Framework Real API Test")
    print("Testing with OpenAI gpt-4o-mini model")
    print("Date: 2025-07-31")
    
    results = []
    
    # Run tests
    results.append(await test_chat_mode())
    results.append(await test_vetting_mode())
    results.append(await test_cost_calculation())
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! The VETTING framework is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the output above.")
    
    return passed == total


if __name__ == "__main__":
    # Run the tests
    success = asyncio.run(main())
    sys.exit(0 if success else 1)