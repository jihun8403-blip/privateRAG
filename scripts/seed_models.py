"""기본 LLM 모델 시드 스크립트."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DEFAULT_MODELS = [
    {
        "provider": "ollama",
        "model_name": "qwen2.5:7b",
        "capability_tags": ["query_gen", "relevance_check", "answer"],
        "daily_budget_tokens": 999_999_999,
        "priority": 1,
        "fallback_order": 1,
        "max_context": 32768,
        "cost_input_per_1k": 0.0,
        "cost_output_per_1k": 0.0,
    },
    {
        "provider": "ollama",
        "model_name": "llama3.2:3b",
        "capability_tags": ["relevance_check", "answer"],
        "daily_budget_tokens": 999_999_999,
        "priority": 2,
        "fallback_order": 2,
        "max_context": 8192,
        "cost_input_per_1k": 0.0,
        "cost_output_per_1k": 0.0,
    },
    {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "capability_tags": ["query_gen", "relevance_check", "answer"],
        "daily_budget_tokens": 100_000,
        "priority": 3,
        "fallback_order": 3,
        "max_context": 128000,
        "cost_input_per_1k": 0.00015,
        "cost_output_per_1k": 0.0006,
    },
    {
        "provider": "anthropic",
        "model_name": "claude-haiku-4-5-20251001",
        "capability_tags": ["query_gen", "relevance_check", "answer"],
        "daily_budget_tokens": 100_000,
        "priority": 4,
        "fallback_order": 4,
        "max_context": 200000,
        "cost_input_per_1k": 0.00025,
        "cost_output_per_1k": 0.00125,
    },
]


async def seed_default_models():
    """기본 모델을 DB에 등록합니다 (이미 존재하면 스킵)."""
    from sqlalchemy import select
    from app.db.session import AsyncSessionLocal
    from app.models.model_registry import ModelRegistry

    async with AsyncSessionLocal() as db:
        for model_data in DEFAULT_MODELS:
            # 이미 존재하는지 확인
            stmt = select(ModelRegistry).where(
                ModelRegistry.provider == model_data["provider"],
                ModelRegistry.model_name == model_data["model_name"],
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                print(f"  - 스킵 (이미 존재): {model_data['provider']}:{model_data['model_name']}")
                continue

            model = ModelRegistry(**model_data, enabled=True)
            db.add(model)
            print(f"  + 등록: {model_data['provider']}:{model_data['model_name']}")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed_default_models())
