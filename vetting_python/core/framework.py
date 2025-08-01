"""
Core VETTING framework implementation.

This module contains the main VettingFramework class that orchestrates
the dual-LLM architecture with architectural policy isolation.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from .models import (
    VettingConfig, ChatMessage, VettingResponse, VerificationResult,
    AttemptDetail, Usage, StopReason, Provider
)

logger = logging.getLogger(__name__)


class VettingFramework:
    """
    Main framework class implementing the VETTING dual-LLM architecture.
    
    The framework separates conversational logic (Chat-Layer) from policy
    enforcement (Verification-Layer) to prevent prompt injection attacks
    on safety rules and enable verifiable policy compliance.
    """
    
    def __init__(
        self,
        chat_provider: Provider,
        verification_provider: Optional[Provider] = None
    ):
        """
        Initialize the VETTING framework.
        
        Args:
            chat_provider: Provider for the Chat-Layer (LLM-A)
            verification_provider: Provider for Verification-Layer (LLM-B).
                                  If None, uses same as chat_provider.
        """
        self.chat_provider = chat_provider
        self.verification_provider = verification_provider or chat_provider
        
        # Default system prompts
        self.default_chat_prompt = (
            "You are a helpful AI tutor. Your primary goal is to guide students "
            "towards understanding concepts and finding answers themselves. "
            "Avoid giving direct answers, especially for factual questions. "
            "Instead, ask guiding questions, provide hints, or suggest related concepts."
        )
        
        logger.info("VETTING framework initialized with dual-LLM architecture")
    
    async def process(
        self,
        messages: List[ChatMessage],
        config: VettingConfig
    ) -> VettingResponse:
        """
        Process messages through the VETTING framework.
        
        Args:
            messages: List of conversation messages
            config: Configuration for the vetting process
            
        Returns:
            VettingResponse with the final result and metadata
        """
        start_time = time.time()
        
        logger.info(f"Processing {len(messages)} messages in {config.mode} mode")
        
        if config.mode == "chat":
            return await self._process_chat_mode(messages, config, start_time)
        else:
            return await self._process_vetting_mode(messages, config, start_time)
    
    async def _process_chat_mode(
        self,
        messages: List[ChatMessage],
        config: VettingConfig,
        start_time: float
    ) -> VettingResponse:
        """Process messages in simple chat mode without verification."""
        
        # Prepare system prompt
        system_prompt = self._prepare_chat_prompt(config)
        
        try:
            # Generate response
            content, usage, requires_attention = await self.chat_provider.generate_response(
                messages=messages,
                model_config=config.chat_model,
                system_prompt=system_prompt
            )
            
            cost = self.chat_provider.calculate_cost(config.chat_model.model_id, usage)
            
            return VettingResponse(
                content=content,
                mode="chat",
                requires_attention=requires_attention,
                attempt_count=1,
                stop_reason=StopReason.NOT_APPLICABLE_CHAT_MODE,
                chat_usage=usage,
                total_usage=usage,
                total_cost=cost,
                processing_time_ms=(time.time() - start_time) * 1000,
                session_id=config.session_id,
                user_id=config.user_id,
                chat_model_used=config.chat_model.model_id
            )
            
        except Exception as e:
            logger.error(f"Error in chat mode: {e}")
            return self._create_error_response(str(e), config, start_time)
    
    async def _process_vetting_mode(
        self,
        messages: List[ChatMessage],
        config: VettingConfig,
        start_time: float
    ) -> VettingResponse:
        """Process messages through the full vetting loop."""
        
        current_messages = messages.copy()
        attempts: List[AttemptDetail] = []
        
        final_content = ""
        overall_verification_passed = False
        final_requires_attention = False
        stop_reason = None
        
        total_chat_usage = Usage()
        total_verification_usage = Usage()
        total_cost = 0.0
        
        # Prepare prompts
        chat_system_prompt = self._prepare_chat_prompt(config)
        verification_system_prompt = self._prepare_verification_prompt(config)
        
        attempt_count = 0
        while attempt_count < config.max_attempts:
            attempt_count += 1
            logger.debug(f"Starting attempt {attempt_count}/{config.max_attempts}")
            
            try:
                # Generate chat response
                content, chat_usage, requires_attention = await self.chat_provider.generate_response(
                    messages=current_messages,
                    model_config=config.chat_model,
                    system_prompt=chat_system_prompt
                )
                
                chat_cost = self.chat_provider.calculate_cost(
                    config.chat_model.model_id, chat_usage
                )
                total_chat_usage += chat_usage
                total_cost += chat_cost
                
                # Check for safety trigger - immediate stop
                if requires_attention:
                    logger.info(f"Safety trigger detected on attempt {attempt_count}")
                    
                    attempts.append(AttemptDetail(
                        attempt_number=attempt_count,
                        chat_response=content,
                        verification_passed=False,
                        verification_output="N/A (Safety Triggered)",
                        requires_attention=True,
                        chat_usage=chat_usage,
                        verification_usage=Usage(),
                        chat_cost=chat_cost,
                        verification_cost=0.0
                    ))
                    
                    return VettingResponse(
                        content=content,
                        mode="vetting",
                        requires_attention=True,
                        verification_passed=False,
                        attempt_count=attempt_count,
                        stop_reason=StopReason.SAFETY_TRIGGERED,
                        attempts=attempts,
                        chat_usage=total_chat_usage,
                        verification_usage=total_verification_usage,
                        total_usage=total_chat_usage + total_verification_usage,
                        total_cost=total_cost,
                        processing_time_ms=(time.time() - start_time) * 1000,
                        session_id=config.session_id,
                        user_id=config.user_id,
                        chat_model_used=config.chat_model.model_id,
                        verification_model_used=config.verification_model.model_id
                    )
                
                # Verify response
                verification_result = await self._verify_response(
                    content, verification_system_prompt, config, attempt_count
                )
                
                verification_cost = self.verification_provider.calculate_cost(
                    config.verification_model.model_id, verification_result.usage
                )
                total_verification_usage += verification_result.usage
                total_cost += verification_cost
                
                # Record attempt
                attempts.append(AttemptDetail(
                    attempt_number=attempt_count,
                    chat_response=content,
                    verification_passed=verification_result.passed,
                    verification_output=verification_result.verification_output,
                    requires_attention=requires_attention,
                    chat_usage=chat_usage,
                    verification_usage=verification_result.usage,
                    chat_cost=chat_cost,
                    verification_cost=verification_cost
                ))
                
                if verification_result.passed:
                    # Success!
                    final_content = content
                    overall_verification_passed = True
                    final_requires_attention = requires_attention
                    stop_reason = StopReason.VERIFICATION_PASSED
                    break
                else:
                    # Failed verification - prepare for retry
                    if attempt_count < config.max_attempts:
                        current_messages.append(ChatMessage("assistant", content))
                        current_messages.append(ChatMessage(
                            "system",
                            f"Your previous response failed verification for the following reason: "
                            f"{verification_result.verification_output}. Please try again, "
                            f"ensuring you adhere to the pedagogical guidelines (guiding, "
                            f"not revealing the answer or key concepts)."
                        ))
                        
                        # Limit history length to prevent excessive token usage
                        if len(current_messages) > 20:
                            current_messages = [current_messages[0]] + current_messages[-19:]
                    else:
                        # Max attempts reached
                        final_content = content
                        final_requires_attention = requires_attention
                        stop_reason = StopReason.MAX_ATTEMPTS_REACHED
                        
            except Exception as e:
                logger.error(f"Error during attempt {attempt_count}: {e}")
                
                if attempt_count == 1:
                    # First attempt failed - return error
                    return self._create_error_response(str(e), config, start_time)
                else:
                    # Use previous response if available
                    if attempts:
                        final_content = attempts[-1].chat_response
                    else:
                        final_content = "Error generating response after multiple attempts."
                    stop_reason = StopReason.GENERATION_ERROR
                    break
        
        # Ensure stop reason is set
        if stop_reason is None:
            stop_reason = StopReason.MAX_ATTEMPTS_REACHED
        
        return VettingResponse(
            content=final_content,
            mode="vetting",
            requires_attention=final_requires_attention,
            verification_passed=overall_verification_passed,
            attempt_count=attempt_count,
            stop_reason=stop_reason,
            attempts=attempts,
            chat_usage=total_chat_usage,
            verification_usage=total_verification_usage,
            total_usage=total_chat_usage + total_verification_usage,
            total_cost=total_cost,
            processing_time_ms=(time.time() - start_time) * 1000,
            session_id=config.session_id,
            user_id=config.user_id,
            chat_model_used=config.chat_model.model_id,
            verification_model_used=config.verification_model.model_id if config.verification_model else None
        )
    
    async def _verify_response(
        self,
        response_content: str,
        verification_system_prompt: str,
        config: VettingConfig,
        attempt_number: int
    ) -> VerificationResult:
        """Verify a chat response using the verification model."""
        
        verification_messages = [
            ChatMessage(
                "user",
                f"Please verify this assistant's response based on the criteria "
                f"and context provided in the system prompt:\n\n"
                f"Assistant Response:\n\"{response_content}\""
            )
        ]
        
        try:
            content, usage, _ = await self.verification_provider.generate_response(
                messages=verification_messages,
                model_config=config.verification_model,
                system_prompt=verification_system_prompt
            )
            
            # Parse verification result
            passed, output = self._parse_verification_result(content)
            
            return VerificationResult(
                passed=passed,
                verification_output=output,
                attempt_number=attempt_number,
                usage=usage,
                cost=self.verification_provider.calculate_cost(
                    config.verification_model.model_id, usage
                )
            )
            
        except Exception as e:
            logger.error(f"Verification error on attempt {attempt_number}: {e}")
            return VerificationResult(
                passed=False,
                verification_output=f"Verification failed: {str(e)}",
                attempt_number=attempt_number,
                usage=Usage(),
                cost=0.0
            )
    
    def _parse_verification_result(self, verification_content: str) -> Tuple[bool, str]:
        """Parse the verification model's response."""
        trimmed = verification_content.strip()
        
        if trimmed.upper() == "PASS":
            return True, "PASS"
        else:
            # Anything else is a failure reason
            reason = trimmed[:500] if trimmed else "FAILED: Reason unspecified."
            return False, reason
    
    def _prepare_chat_prompt(self, config: VettingConfig) -> str:
        """Prepare the system prompt for the chat model."""
        
        base_prompt = config.chat_system_prompt or self.default_chat_prompt
        
        # Add context from questions if provided
        if config.context_items:
            base_prompt += "\n\n--- Context Questions ---"
            for i, item in enumerate(config.context_items, 1):
                if "text" in item.question:
                    base_prompt += f"\n\nQuestion {i}:"
                    if "id" in item.question:
                        base_prompt += f" (ID: {item.question['id']})"
                    if "subject" in item.question:
                        base_prompt += f"\nSubject: {item.question['subject']}"
                    base_prompt += f"\nText: {item.question['text']}"
            base_prompt += "\n--- End Context Questions ---"
        
        # Add current date/time
        now = datetime.utcnow()
        base_prompt += f"\n\n--- Current Environment Information ---"
        base_prompt += f"\nCurrent Date: {now.strftime('%Y-%m-%d')}"
        base_prompt += f"\nCurrent Time: {now.strftime('%H:%M:%S')} UTC"
        base_prompt += f"\n--- End Current Environment Information ---"
        
        # Add educational interaction rule if enabled
        if config.enable_educational_rules:
            base_prompt += (
                "\n\nIMPORTANT PEDAGOGICAL RULE: When responding to the student, "
                "always conclude your message with a thoughtful question. This question "
                "should be designed to encourage the student to reflect more deeply on "
                "the topic, consider alternative perspectives, or guide their self-regulation "
                "and learning process. For example, ask 'What makes you think that?', "
                "'How does this connect to what we discussed earlier?', or 'What steps "
                "could you take to explore this further?'. Ensure the question is "
                "open-ended and promotes critical thinking."
            )
        
        # Add safety prefix instruction if enabled
        if config.enable_safety_prefix:
            base_prompt += (
                "\n\nIMPORTANT SAFETY RULE: If you perceive the user's query or the "
                "topic of conversation relates to potentially harmful, unethical, illegal, "
                "or dangerous subjects (e.g., self-harm, violence, severe safety risks, "
                "hate speech, non-consensual sexual content), your response MUST follow "
                "these steps: 1. Prefix your entire response *exactly* with "
                "'[REQUIRES_ATTENTION] '. 2. Express care and concern for the user's "
                "well-being in a non-judgmental way. 3. Gently refuse to provide harmful "
                "information or instructions *if applicable*. 4. Strongly encourage seeking "
                "help from qualified professionals, trusted adults, or safety resources "
                "(emphasize seeking help, no need to list specific resources). "
                "For all other topics, respond normally without the prefix or these specific steps."
            )
        
        return base_prompt
    
    def _prepare_verification_prompt(self, config: VettingConfig) -> str:
        """Prepare the system prompt for the verification model."""
        
        if config.verification_system_prompt:
            base_prompt = config.verification_system_prompt
        else:
            # Default verification prompt
            chat_prompt_ref = config.chat_system_prompt or self.default_chat_prompt
            base_prompt = (
                f"You are an evaluation assistant. Your task is to determine if the "
                f"following chat response adheres to the pedagogical guidelines set in "
                f"the initial system prompt provided to the chat assistant. The goal is "
                f"to guide the student without giving away the direct answers or key "
                f"concepts mentioned in the provided answer keys.\n\n"
                f"Initial Chat System Prompt provided to the assistant being evaluated:\n"
                f"---\n{chat_prompt_ref}\n---"
            )
        
        # Add context from questions and answer keys if provided
        if config.context_items:
            all_answers = []
            all_key_concepts = []
            
            base_prompt += "\n\n--- Context Questions & Answers for Verification ---"
            for i, item in enumerate(config.context_items, 1):
                question_text = item.question.get("text", "")
                
                if item.answer_key:
                    answer_text = item.answer_key.get("correctAnswer", "")
                    if question_text and answer_text:
                        base_prompt += f"\n\nQuestion {i}:"
                        if "id" in item.question:
                            base_prompt += f" (ID: {item.question['id']})"
                        base_prompt += f"\nText: {question_text}"
                        base_prompt += f"\nCorrect Answer {i}: {answer_text}"
                        all_answers.append(answer_text)
                        
                        key_concepts = item.answer_key.get("keyConcepts", [])
                        if key_concepts:
                            base_prompt += f"\nKey Concepts {i}: {', '.join(key_concepts)}"
                            all_key_concepts.extend(key_concepts)
                        
                        explanation = item.answer_key.get("explanation", "")
                        if explanation:
                            base_prompt += f"\nExplanation/Context {i}: {explanation}"
            
            base_prompt += "\n--- End Context Questions & Answers ---"
            
            # Add evaluation criteria
            answer_check = f"({' or '.join(f'{repr(a)}' for a in all_answers)})" if all_answers else "(any of the correct answers)"
            concepts_check = f"({' or '.join(f'{repr(c)}' for c in all_key_concepts)})" if all_key_concepts else "(any of the key concepts)"
            
            base_prompt += f"""

Evaluate the assistant's response provided below based on these criteria:
1. Does the response directly reveal any of the correct answers {answer_check} or explicitly state any of the key concepts {concepts_check}? (FAIL if yes)
2. Does the response guide the student towards understanding or finding the answers themselves? (PASS if yes)
3. Is the response relevant to the student's query and the question context? (FAIL if irrelevant)

Please analyze the assistant's response provided below. After your analysis, output EXACTLY ONE of the following verdicts:
- "PASS" if the response meets the criteria.
- A concise reason (1-2 sentences) explaining specifically WHY the response failed the criteria (e.g., "FAILED: Directly states the answer 'Paris'." or "FAILED: Reveals the key concept 'TCP'.").

DO NOT include any other commentary, preamble, or explanation. Your entire output should be just "PASS" or the failure reason."""
        
        return base_prompt
    
    def _create_error_response(
        self,
        error_message: str,
        config: VettingConfig,
        start_time: float
    ) -> VettingResponse:
        """Create an error response."""
        return VettingResponse(
            content=f"Error: {error_message}",
            mode=config.mode,
            requires_attention=False,
            verification_passed=False if config.mode == "vetting" else None,
            attempt_count=1,
            stop_reason=StopReason.GENERATION_ERROR,
            processing_time_ms=(time.time() - start_time) * 1000,
            session_id=config.session_id,
            user_id=config.user_id,
            chat_model_used=config.chat_model.model_id,
            verification_model_used=config.verification_model.model_id if config.verification_model else None
        )