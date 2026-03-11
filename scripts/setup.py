"""초기 설정 스크립트 — 디렉터리 생성, DB 초기화, Qdrant 컬렉션 생성."""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    print("=== PrivateRAG 초기 설정 시작 ===")

    # 1. 디렉터리 생성
    dirs = [
        "data/raw", "data/normalized", "data/archive", "data/index",
        "config", "scripts",
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    print("✓ 디렉터리 생성 완료")

    # 2. DB 초기화
    from app.db.session import engine
    from app.db.base import Base
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("✓ SQLite DB 초기화 완료")

    # 3. Qdrant 컬렉션 생성
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PayloadSchemaType
        from app.core.config import settings

        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        collections = [c.name for c in qdrant.get_collections().collections]
        if settings.qdrant_collection not in collections:
            qdrant.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(
                    size=settings.embedding_dimension,
                    distance=Distance.COSINE,
                ),
                on_disk_payload=True,
            )
            print(f"✓ Qdrant 컬렉션 '{settings.qdrant_collection}' 생성 완료")
        else:
            print(f"✓ Qdrant 컬렉션 '{settings.qdrant_collection}' 이미 존재")
    except Exception as e:
        print(f"⚠ Qdrant 초기화 실패 (Qdrant 서버가 실행 중인지 확인): {e}")

    # 4. 기본 모델 시드
    from scripts.seed_models import seed_default_models
    await seed_default_models()
    print("✓ 기본 모델 등록 완료")

    print("\n=== 초기 설정 완료 ===")
    print("다음 명령으로 서버를 시작하세요:")
    print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    asyncio.run(main())
