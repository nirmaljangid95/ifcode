"""
LLM Client - Abstraction layer for language model inference.

Supports multiple providers: Ollama (local), OpenAI-compatible APIs, and custom endpoints.
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Response from LLM inference."""
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""
    success: bool = True
    error: Optional[str] = None


class LLMClient:
    """
    Universal LLM client supporting multiple inference providers.
    
    Supported providers:
    - ollama: Local Ollama server
    - openai: OpenAI or OpenAI-compatible APIs
    - custom: Custom HTTP endpoint
    """
    
    def __init__(
        self,
        provider: str = "ollama",
        model: str = "llama3.2:3b",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        timeout: int = 60,
    ):
        """
        Initialize LLM client.
        
        Args:
            provider: Provider name (ollama, openai, custom)
            model: Model identifier
            base_url: Base URL for API endpoint
            api_key: API key for authentication
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            timeout: Request timeout in seconds
        """
        self.provider = provider.lower()
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Set defaults based on provider
        if self.provider == "ollama":
            self.base_url = base_url or "http://localhost:11434"
            self.api_key = None
        elif self.provider == "openai":
            self.base_url = base_url or "https://api.openai.com/v1"
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        else:
            self.base_url = base_url
            self.api_key = api_key
        
        # Initialize client based on provider
        self._client = None
        self._init_client()
        
        logger.info(f"Initialized LLM client: provider={self.provider}, model={self.model}")
    
    def _init_client(self):
        """Initialize the appropriate client library."""
        try:
            if self.provider == "ollama":
                import ollama
                self._client = ollama
                logger.debug("Ollama client initialized")
            
            elif self.provider == "openai":
                from openai import OpenAI
                self._client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout
                )
                logger.debug("OpenAI client initialized")
            
            else:
                logger.warning(f"Unknown provider: {self.provider}. Will attempt direct HTTP.")
        
        except ImportError as e:
            logger.error(f"Failed to import client library for {self.provider}: {e}")
            raise RuntimeError(
                f"Client library not installed for provider '{self.provider}'. "
                f"Install with: pip install {self.provider}"
            )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Generate completion from the LLM.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt for context
            temperature: Override default temperature
            max_tokens: Override default max tokens
        
        Returns:
            LLMResponse with generated content and metadata
        """
        temp = temperature if temperature is not None else self.temperature
        max_tok = max_tokens if max_tokens is not None else self.max_tokens
        
        try:
            if self.provider == "ollama":
                return self._generate_ollama(prompt, system_prompt, temp, max_tok)
            elif self.provider == "openai":
                return self._generate_openai(prompt, system_prompt, temp, max_tok)
            else:
                raise NotImplementedError(f"Provider {self.provider} not yet supported")
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return LLMResponse(
                content="",
                success=False,
                error=str(e)
            )
    
    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Generate using Ollama."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self._client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            )
            
            content = response.get("message", {}).get("content", "")
            
            return LLMResponse(
                content=content,
                prompt_tokens=response.get("prompt_eval_count", 0),
                completion_tokens=response.get("eval_count", 0),
                model=self.model,
                success=True
            )
        
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise
    
    def _generate_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int
    ) -> LLMResponse:
        """Generate using OpenAI-compatible API."""
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            content = response.choices[0].message.content
            
            return LLMResponse(
                content=content,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                model=response.model,
                success=True
            )
        
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test if the LLM connection is working.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self.generate(
                prompt="Respond with: OK",
                temperature=0.0,
                max_tokens=10
            )
            return response.success and "OK" in response.content.upper()
        
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def __repr__(self) -> str:
        return f"LLMClient(provider={self.provider}, model={self.model})"
