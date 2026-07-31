import asyncio
import gc
import os
import time
from contextlib import asynccontextmanager

import uvicorn
from core.infrastructure.logging.logger import get_logger
from core.infrastructure.services.llm_runner import LocalLlmRunner
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

load_dotenv()

logger = get_logger("agent-llm-runner")

# Global singleton runner and concurrency lock
runner: LocalLlmRunner | None = None
inference_lock = asyncio.Lock()
last_used_time = time.time()
active_requests_count = 0


class ChatCompletionRequest(BaseModel):
    messages: list[dict[str, str]]
    max_tokens: int = 512
    temperature: float = 0.0
    response_format: dict | None = None


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: dict[str, str]
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-local"
    object: str = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str = "local-gguf"
    choices: list[ChatCompletionChoice]


class HealthResponse(BaseModel):
    status: str
    is_loaded: bool
    active_requests: int
    idle_seconds: float
    model_path: str


def get_llm_config() -> dict:
    model_path = os.environ.get(
        "MODEL_PATH",
        "unsloth/gemma-4-E2B-it-GGUF/gemma-4-E2B-it-Q4_K_M.gguf",
    )
    models_dir = os.environ.get("MODELS_DIR", "models")
    max_length = int(
        os.environ.get("MAX_CONTEXT_TOKENS", os.environ.get("MAX_LENGTH", "8192"))
    )
    temperature = float(os.environ.get("TEMPERATURE", "0.0"))
    idle_timeout = float(os.environ.get("MODEL_IDLE_TIMEOUT", "60.0"))
    return {
        "model_path": model_path,
        "models_dir": models_dir,
        "max_length": max_length,
        "temperature": temperature,
        "idle_timeout": idle_timeout,
    }


async def idle_checker_loop():
    global runner, last_used_time
    config = get_llm_config()
    idle_timeout = config["idle_timeout"]

    while True:
        await asyncio.sleep(10.0)
        if runner is not None and runner.is_loaded:
            if active_requests_count == 0 and (time.time() - last_used_time) > idle_timeout:
                logger.info(
                    f"LLM Service: Idle timeout reached ({idle_timeout}s). "
                    f"Unloading model weights from RAM..."
                )
                async with inference_lock:
                    runner.free_model()
                    gc.collect()
                logger.info("LLM Service: Model RAM freed successfully!")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    config = get_llm_config()
    runner = LocalLlmRunner(
        model_path=config["model_path"],
        models_dir=config["models_dir"],
        max_context=config["max_length"],
        temperature=config["temperature"],
    )
    logger.info(
        f"LLM Service pre-loading model weights from '{config['model_path']}'..."
    )
    runner.load_model()
    logger.info("LLM Service model pre-loaded successfully!")
    checker_task = asyncio.create_task(idle_checker_loop())
    yield
    checker_task.cancel()
    if runner is not None:
        runner.free_model()


app = FastAPI(
    title="Centralized LLM Runner Service",
    description="High-Performance GGUF LLM Runner with OpenAI-compatible endpoint",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    global runner, last_used_time, active_requests_count
    config = get_llm_config()
    is_loaded = runner.is_loaded if runner else False
    idle_seconds = time.time() - last_used_time
    return HealthResponse(
        status="ok",
        is_loaded=is_loaded,
        active_requests=active_requests_count,
        idle_seconds=round(idle_seconds, 2),
        model_path=config["model_path"],
    )


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(req: ChatCompletionRequest):
    global runner, last_used_time, active_requests_count
    if runner is None:
        raise HTTPException(status_code=500, detail="LLM Runner service not initialized")

    active_requests_count += 1
    try:
        async with inference_lock:
            last_used_time = time.time()
            # Perform inference inside lock
            output_text = await asyncio.to_thread(
                runner.create_chat_completion,
                messages=req.messages,
                max_tokens=req.max_tokens,
                response_format=req.response_format,
            )
            last_used_time = time.time()

        return ChatCompletionResponse(
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message={"role": "assistant", "content": output_text},
                    finish_reason="stop",
                )
            ]
        )
    except Exception as e:
        logger.error(f"LLM Inference failed: {e}")
        raise HTTPException(status_code=500, detail=f"LLM Inference error: {e}")
    finally:
        active_requests_count -= 1


def main():
    port = int(os.environ.get("LLM_SERVICE_PORT", "8001"))
    host = os.environ.get("LLM_SERVICE_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
