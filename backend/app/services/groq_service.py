"""
Groq AI service for fast, free inference.
"""

import os
from typing import Optional, List, Dict, Any
from groq import AsyncGroq

# Groq free models (very fast inference)
MODELS = {
    "fast": "llama-3.1-8b-instant",  # Fast, free
    "powerful": "llama-3.1-70b-versatile",  # More powerful, still free
    "reasoning": "deepseek-r1-distill-llama-70b",  # Best for reasoning
}


class GroqService:
    def __init__(self):
        api_key = os.getenv(
            "GROQ_API_KEY", "gsk_GGjAhjuK2NqW6kNAD68WGdyb3FY6vgPWSP6beLdntk3B6Xdxqec"
        )
        self._client = AsyncGroq(api_key=api_key)

    def is_available(self) -> bool:
        return True

    async def chat(
        self,
        prompt: str,
        model: str = "powerful",
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> str:
        """Generate a chat completion."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        model_name = MODELS.get(model, MODELS["powerful"])

        response = await self._client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
        )

        return response.choices[0].message.content

    async def analyze_trading_signal(
        self,
        price: float,
        rsi: float,
        momentum: float,
        volume_ratio: float,
        position: str,
    ) -> Dict[str, Any]:
        """Analyze trading conditions and provide insights."""
        prompt = f"""Analiza las siguientes condiciones de mercado para BTC/USD y proporciona una recomendación de trading:

- Precio actual: ${price:,.2f}
- RSI: {rsi:.1f}
- Momentum: {momentum * 100:.2f}%
- Ratio volumen: {volume_ratio:.2f}
- Posición actual: {position}

Responde en formato JSON con:
{{
    "action": "buy/sell/hold",
    "confidence": 0.0-1.0,
    "reason": "explicación breve",
    "risk_level": "low/medium/high",
    "tp_signal": true/false,
    "sl_signal": true/false
}}
"""

        try:
            result = await self.chat(prompt, model="powerful", temperature=0.3)
            # Try to parse JSON from result
            import json
            import re

            # Extract JSON from response
            match = re.search(r"\{.*\}", result, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            print(f"Error analyzing signal: {e}")

        return {
            "action": "hold",
            "confidence": 0.5,
            "reason": "Error en análisis",
            "risk_level": "medium",
            "tp_signal": False,
            "sl_signal": False,
        }


# Singleton instance
groq_service = GroqService()
