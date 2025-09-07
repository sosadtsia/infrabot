"""
Ollama client wrapper for model management and availability checking
"""

import requests
import json
from typing import Optional, Dict, Any

class OllamaClient:
    """Wrapper for Ollama API interactions"""

    def __init__(self, model: str = "deepseek-coder", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_url = f"{self.base_url}/api"

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available"""
        try:
            # Check if Ollama service is running
            response = requests.get(f"{self.base_url}/", timeout=5)
            if response.status_code != 200:
                return False

            # Check if our model is available
            return self.is_model_available()

        except requests.exceptions.RequestException:
            return False

    def is_model_available(self) -> bool:
        """Check if the specified model is available"""
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'].split(':')[0] for model in models]
                return self.model in model_names or self.model in [m['name'] for m in models]
            return False
        except requests.exceptions.RequestException:
            return False

    def list_models(self) -> list:
        """List all available models"""
        try:
            response = requests.get(f"{self.api_url}/tags", timeout=10)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [{'name': m['name'], 'size': m.get('size', 0)} for m in models]
            return []
        except requests.exceptions.RequestException:
            return []

    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry"""
        try:
            response = requests.post(
                f"{self.api_url}/pull",
                json={"name": model_name},
                timeout=300  # 5 minutes timeout for model pulling
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False

    def generate(self, prompt: str, **kwargs) -> Optional[str]:
        """Generate text using the model"""
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                **kwargs
            }

            response = requests.post(
                f"{self.api_url}/generate",
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                return response.json().get('response', '')
            return None

        except requests.exceptions.RequestException:
            return None

    def chat(self, messages: list, **kwargs) -> Optional[str]:
        """Chat with the model"""
        try:
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                **kwargs
            }

            response = requests.post(
                f"{self.api_url}/chat",
                json=payload,
                timeout=120
            )

            if response.status_code == 200:
                result = response.json()
                return result.get('message', {}).get('content', '')
            return None

        except requests.exceptions.RequestException:
            return None

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model"""
        try:
            response = requests.post(
                f"{self.api_url}/show",
                json={"name": self.model},
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            return {}

        except requests.exceptions.RequestException:
            return {}

    def health_check(self) -> Dict[str, Any]:
        """Perform a comprehensive health check"""
        health = {
            "service_running": False,
            "model_available": False,
            "model_info": {},
            "available_models": [],
            "response_test": False
        }

        try:
            # Check service
            response = requests.get(f"{self.base_url}/", timeout=5)
            health["service_running"] = response.status_code == 200

            if health["service_running"]:
                # Check model
                health["model_available"] = self.is_model_available()
                health["available_models"] = self.list_models()

                if health["model_available"]:
                    # Get model info
                    health["model_info"] = self.get_model_info()

                    # Test response
                    test_response = self.generate("Hello", max_tokens=5)
                    health["response_test"] = test_response is not None

        except Exception as e:
            health["error"] = str(e)

        return health
