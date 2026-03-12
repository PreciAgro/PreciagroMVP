# Runbook: Integrating Real LLM Models into Conversational NLP Engine

This runbook explains how to plug in real LLM models to replace the stub backend in the Conversational NLP engine.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Supported Backends](#supported-backends)
4. [Integration Steps by Provider](#integration-steps-by-provider)
5. [Testing Your Integration](#testing-your-integration)
6. [Troubleshooting](#troubleshooting)
7. [Advanced Configuration](#advanced-configuration)

---

## Overview

The Conversational NLP engine uses a pluggable backend architecture. By default, it uses a `StubAgroLLMBackend` that provides deterministic responses for testing. To use real LLM models, you need to:

1. Choose a backend provider
2. Install required dependencies
3. Configure environment variables
4. Implement the backend methods (if using a custom provider)
5. Test the integration

The engine supports two main operations:
- **Classification**: Intent and entity extraction from user messages
- **Generation**: Response generation with context from tools and RAG

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Conversational NLP Engine                       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │         AgroLLMClient (Interface)                 │  │
│  │  - classify_intent_and_entities()                 │  │
│  │  - generate_answer()                              │  │
│  └──────────────────────────────────────────────────┘  │
│                        │                                 │
│                        ▼                                 │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Backend (Protocol)                       │  │
│  │  - classify(payload) -> Dict                    │  │
│  │  - generate(payload) -> Dict                    │  │
│  └──────────────────────────────────────────────────┘  │
│                        │                                 │
│        ┌───────────────┼───────────────┐                │
│        ▼               ▼               ▼                │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐            │
│  │ OpenAI  │   │Anthropic │   │ Ollama   │            │
│  │ Backend │   │ Backend  │   │ Backend  │            │
│  └─────────┘   └──────────┘   └──────────┘            │
│                                                          │
│  ┌─────────┐   ┌──────────┐   ┌──────────┐            │
│  │  vLLM   │   │   HTTP   │   │  Stub    │            │
│  │ Backend │   │ Backend  │   │ Backend  │            │
│  └─────────┘   └──────────┘   └──────────┘            │
└─────────────────────────────────────────────────────────┘
```

The `AgroLLMClient` builds standardized payloads and calls the backend's `classify()` or `generate()` methods. Each backend must return structured JSON matching the expected schema.

---

## Supported Backends

| Backend | Status | Use Case | Cost |
|---------|--------|----------|------|
| **stub** | ✅ Ready | Testing/Development | Free |
| **http** | ✅ Ready | Custom API endpoints | Varies |
| **openai** | 🟡 Placeholder | Production (cloud) | Pay-per-use |
| **anthropic** | 🟡 Placeholder | Production (cloud) | Pay-per-use |
| **ollama** | 🟡 Placeholder | Local development | Free |
| **vllm** | 🟡 Placeholder | Self-hosted production | Infrastructure |

**Status Legend:**
- ✅ Ready: Fully implemented and tested
- 🟡 Placeholder: Structure ready, needs implementation
- ❌ Not supported: Not available

---

## Integration Steps by Provider

### 1. OpenAI (GPT-4, GPT-3.5)

**Best for:** Production deployments with high-quality responses and fast inference.

#### Step 1: Install Dependencies

```bash
pip install openai>=1.0.0
```

#### Step 2: Get API Key

1. Sign up at https://platform.openai.com
2. Create an API key in your account settings
3. Store it securely (use environment variables, not code)

#### Step 3: Configure Environment Variables

```bash
# Set backend to OpenAI
export AGROLLM_BACKEND=openai

# Required: API key
export OPENAI_API_KEY=sk-...

# Optional: Model selection (defaults to gpt-4)
export OPENAI_MODEL=gpt-4
export OPENAI_CLASSIFY_MODEL=gpt-3.5-turbo  # Use cheaper model for classification
export OPENAI_GENERATE_MODEL=gpt-4          # Use better model for generation

# Optional: Custom base URL (for Azure OpenAI or proxies)
export OPENAI_BASE_URL=https://api.openai.com/v1

# Timeout (default 15s)
export AGROLLM_TIMEOUT_SECONDS=30
```

#### Step 4: Implement Backend Methods

Edit `preciagro/packages/engines/conversational_nlp/services/agrollm_client.py`:

**For `classify()` method in `OpenAIBackend`:**

```python
async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not self.available:
        return None
    
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds
        )
        
        prompt_data = json.loads(payload.get("prompt", "{}"))
        messages = [
            {
                "role": "system",
                "content": prompt_data.get("instructions", "Classify the user's intent.")
            },
            {
                "role": "user",
                "content": json.dumps(prompt_data)
            }
        ]
        
        response = await client.chat.completions.create(
            model=self.classify_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=500
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "intent": result.get("intent", "general_question"),
            "entities": result.get("entities", {}),
            "confidence": result.get("confidence", 0.8),
            "schema_version": payload.get("schema_version", "v0")
        }
    except Exception as exc:
        logger.error("OpenAI classification failed: %s", exc)
        return None
```

**For `generate()` method:**

```python
async def generate(self, payload: Dict[str, Any]) -> Optional[Any]:
    if not self.available:
        return None
    
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout_seconds
        )
        
        prompt = payload.get("prompt", "")
        messages = [
            {"role": "system", "content": "You are an agricultural assistant."},
            {"role": "user", "content": prompt}
        ]
        
        response = await client.chat.completions.create(
            model=self.generate_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=1500
        )
        
        result = json.loads(response.choices[0].message.content)
        return {
            "summary": result.get("summary", ""),
            "steps": result.get("steps", []),
            "warnings": result.get("warnings", []),
            "extras": result.get("extras", {})
        }
    except Exception as exc:
        logger.error("OpenAI generation failed: %s", exc)
        return None
```

#### Step 5: Test

```bash
# Start the engine
uvicorn preciagro.packages.engines.conversational_nlp.app:app --port 8103

# Test with curl
curl -X POST http://localhost:8103/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "message_id": "test-1",
    "session_id": "sess-1",
    "channel": "web",
    "user": {"user_id": "u1", "tenant_id": "t1", "farm_id": "f1", "role": "farmer"},
    "text": "When should I plant maize in Murewa?"
  }'
```

---

### 2. Anthropic (Claude)

**Best for:** Production with strong safety and reasoning capabilities.

#### Step 1: Install Dependencies

```bash
pip install anthropic>=0.18.0
```

#### Step 2: Get API Key

1. Sign up at https://console.anthropic.com
2. Create an API key
3. Store securely

#### Step 3: Configure Environment Variables

```bash
export AGROLLM_BACKEND=anthropic
export ANTHROPIC_API_KEY=sk-ant-...
export ANTHROPIC_MODEL=claude-3-opus-20240229
export ANTHROPIC_CLASSIFY_MODEL=claude-3-sonnet-20240229  # Optional: cheaper for classification
export ANTHROPIC_GENERATE_MODEL=claude-3-opus-20240229    # Optional: better for generation
```

#### Step 4: Implement Backend Methods

Similar to OpenAI, but using Anthropic's API:

```python
async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not self.available:
        return None
    
    try:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        
        prompt_data = json.loads(payload.get("prompt", "{}"))
        system_prompt = prompt_data.get("instructions", "Classify the user's intent.")
        user_message = json.dumps(prompt_data)
        
        message = await client.messages.create(
            model=self.classify_model,
            max_tokens=500,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            temperature=0.1
        )
        
        # Extract JSON from response (Claude may wrap it in text)
        content = message.content[0].text
        result = json.loads(content)
        
        return {
            "intent": result.get("intent", "general_question"),
            "entities": result.get("entities", {}),
            "confidence": result.get("confidence", 0.8),
            "schema_version": payload.get("schema_version", "v0")
        }
    except Exception as exc:
        logger.error("Anthropic classification failed: %s", exc)
        return None
```

---

### 3. Ollama (Local Models)

**Best for:** Local development, offline use, cost control.

#### Step 1: Install Ollama

```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: Download from https://ollama.ai/download
```

#### Step 2: Pull a Model

```bash
# Recommended models for agriculture:
ollama pull llama2          # General purpose
ollama pull mistral         # Good balance
ollama pull codellama       # If you need code generation
ollama pull qwen:7b         # Multilingual support
```

#### Step 3: Configure Environment Variables

```bash
export AGROLLM_BACKEND=ollama
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama2
export OLLAMA_CLASSIFY_MODEL=llama2    # Optional: different model for classification
export OLLAMA_GENERATE_MODEL=mistral   # Optional: different model for generation
```

#### Step 4: Implement Backend Methods

```python
async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not self.available:
        return None
    
    try:
        prompt = payload.get("prompt", "")
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.classify_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an intent classifier. Return only valid JSON."
                        },
                        {
                            "role": "user",
                            "content": f"{prompt}\n\nReturn JSON with keys: intent, entities, confidence, schema_version"
                        }
                    ],
                    "format": "json",
                    "stream": False
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Ollama returns {"message": {"content": "..."}}
            content = data.get("message", {}).get("content", "{}")
            result = json.loads(content)
            
            return {
                "intent": result.get("intent", "general_question"),
                "entities": result.get("entities", {}),
                "confidence": result.get("confidence", 0.7),
                "schema_version": payload.get("schema_version", "v0")
            }
    except Exception as exc:
        logger.error("Ollama classification failed: %s", exc)
        return None
```

**Note:** Ollama models may not always return valid JSON. Consider adding retry logic or JSON extraction from text.

---

### 4. vLLM (Self-Hosted High-Performance)

**Best for:** Self-hosted production with high throughput.

#### Step 1: Set Up vLLM Server

```bash
# Install vLLM
pip install vllm

# Start server (example with Llama 2)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --port 8000 \
  --host 0.0.0.0
```

#### Step 2: Configure Environment Variables

```bash
export AGROLLM_BACKEND=vllm
export VLLM_BASE_URL=http://localhost:8000
export VLLM_MODEL=meta-llama/Llama-2-7b-chat-hf
export VLLM_CLASSIFY_MODEL=...  # Optional
export VLLM_GENERATE_MODEL=...  # Optional
```

#### Step 3: Implement Backend Methods

vLLM exposes an OpenAI-compatible API, so implementation is similar to OpenAI:

```python
async def classify(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not self.available:
        return None
    
    try:
        prompt = payload.get("prompt", "")
        
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json={
                    "model": self.classify_model,
                    "messages": [
                        {"role": "system", "content": "You are an intent classifier."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
            )
            response.raise_for_status()
            data = response.json()
            
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            
            return {
                "intent": result.get("intent", "general_question"),
                "entities": result.get("entities", {}),
                "confidence": result.get("confidence", 0.8),
                "schema_version": payload.get("schema_version", "v0")
            }
    except Exception as exc:
        logger.error("vLLM classification failed: %s", exc)
        return None
```

---

### 5. Custom HTTP Backend

**Best for:** Custom LLM APIs or proxy services.

#### Step 1: Configure Environment Variables

```bash
export AGROLLM_BACKEND=http
export AGROLLM_CLASSIFY_URL=https://your-api.com/classify
export AGROLLM_GENERATE_URL=https://your-api.com/generate
export AGROLLM_API_KEY=your-api-key
```

#### Step 2: Ensure API Contract

Your API endpoints must accept and return the following formats:

**Classification Request:**
```json
{
  "prompt": "JSON string with instructions, message, session_context, examples",
  "schema_version": "v0",
  "message": {...},
  "session_context": {...}
}
```

**Classification Response:**
```json
{
  "intent": "plan_planting",
  "entities": {"crop": "maize", "location": "Murewa"},
  "confidence": 0.85,
  "schema_version": "v0"
}
```

**Generation Request:**
```json
{
  "prompt": "Full prompt string",
  "message": {...},
  "intent": {...},
  "session_context": {...},
  "tools_context": {...},
  "rag_context": [...]
}
```

**Generation Response:**
```json
{
  "summary": "Main answer text",
  "steps": ["step1", "step2"],
  "warnings": ["warning1"],
  "extras": {}
}
```

The `HTTPAgroLLMBackend` is already implemented and will work with any API matching this contract.

---

## Testing Your Integration

### 1. Health Check

```bash
curl http://localhost:8103/health
```

Should return `{"status": "healthy", "backend": "openai"}` (or your backend name).

### 2. Test Classification

```python
# test_classify.py
import asyncio
from preciagro.packages.engines.conversational_nlp.services.agrollm_client import build_agrollm_client
from preciagro.packages.engines.conversational_nlp.core.config import settings
from preciagro.packages.engines.conversational_nlp.models import ChatMessageRequest, SessionContext

async def test():
    client = build_agrollm_client(settings)
    request = ChatMessageRequest(
        message_id="test-1",
        session_id="sess-1",
        channel="web",
        user={"user_id": "u1", "tenant_id": "t1", "farm_id": "f1", "role": "farmer"},
        text="When should I plant maize?"
    )
    session = SessionContext(session_id="sess-1", user_id="u1")
    
    result = await client.classify_intent_and_entities(request, session)
    print(f"Intent: {result.intent}")
    print(f"Entities: {result.entities}")

asyncio.run(test())
```

### 3. Test Full Pipeline

```bash
# Use the test suite
pytest preciagro/packages/engines/conversational_nlp/tests/test_chat.py -v

# Or manual API test
curl -X POST http://localhost:8103/chat/message \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_KEY" \
  -d @test_message.json
```

---

## Troubleshooting

### Issue: Backend returns None

**Symptoms:** Responses fall back to stub backend.

**Solutions:**
1. Check API key is set: `echo $OPENAI_API_KEY` (or equivalent)
2. Verify backend is selected: Check logs for "Using backend: openai"
3. Check network connectivity: `curl https://api.openai.com/v1/models`
4. Review error logs: Look for exceptions in engine logs

### Issue: Invalid JSON Response

**Symptoms:** `JSONDecodeError` in logs.

**Solutions:**
1. Add JSON extraction logic for models that wrap JSON in text
2. Use `response_format={"type": "json_object"}` for OpenAI
3. Add retry logic with prompt refinement
4. Validate response before parsing

### Issue: Timeout Errors

**Symptoms:** `TimeoutException` in logs.

**Solutions:**
1. Increase timeout: `export AGROLLM_TIMEOUT_SECONDS=60`
2. Use faster models for classification (e.g., `gpt-3.5-turbo` instead of `gpt-4`)
3. Reduce prompt size or context window
4. Check network latency to API

### Issue: Rate Limiting

**Symptoms:** 429 errors from API.

**Solutions:**
1. Implement exponential backoff in backend
2. Add request queuing
3. Use multiple API keys with rotation
4. Reduce request frequency

### Issue: High Costs

**Symptoms:** Unexpected API costs.

**Solutions:**
1. Use cheaper models for classification (`gpt-3.5-turbo`, `claude-3-sonnet`)
2. Cache classification results for similar messages
3. Use local models (Ollama/vLLM) for development
4. Monitor usage with API dashboards

---

## Advanced Configuration

### Using Different Models for Classification vs Generation

Set separate models to optimize cost and performance:

```bash
# OpenAI example
export OPENAI_CLASSIFY_MODEL=gpt-3.5-turbo    # Fast, cheap
export OPENAI_GENERATE_MODEL=gpt-4            # Better quality

# Anthropic example
export ANTHROPIC_CLASSIFY_MODEL=claude-3-sonnet-20240229
export ANTHROPIC_GENERATE_MODEL=claude-3-opus-20240229
```

### Custom System Prompts

Override the default system prompt:

```bash
export CONVERSATION_SYSTEM_PROMPT="You are an expert agricultural advisor specializing in smallholder farming in Zimbabwe and Poland. Always provide practical, actionable advice."
```

### Fallback Behavior

The engine automatically falls back to the stub backend if:
- The primary backend is unavailable
- An API call fails
- A timeout occurs

To disable fallback (fail fast), modify `build_agrollm_client()` to not pass a fallback.

### Monitoring

Check backend usage in metrics:

```bash
curl http://localhost:8103/metrics | grep conversational
```

Look for:
- `conversational_engine_backend` - Current backend name
- `fallback_used_total` - Number of fallbacks
- `chat_requests_total` - Request count by status

---

## Next Steps

1. **Implement your chosen backend** following the examples above
2. **Test thoroughly** with real agricultural queries
3. **Monitor costs and performance** in production
4. **Fine-tune prompts** for better agricultural domain understanding
5. **Consider fine-tuning** models on agricultural data for better performance

---

## Support

For issues or questions:
- Check engine logs: `logs/conversational_nlp.log`
- Review test failures: `pytest preciagro/packages/engines/conversational_nlp/tests -v`
- See architecture docs: `docs/engines/conversational_nlp.md`

---

**Last Updated:** January 2025  
**Maintained By:** PreciAgro Engineering Team


