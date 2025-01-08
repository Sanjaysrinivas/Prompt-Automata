from __future__ import annotations

from src.app import app, db
from src.app.models.fence import Fence
from src.app.models.prompt import Prompt


def migrate_prompts():
    with app.app_context():
        prompts = Prompt.query.all()

        for prompt in prompts:
            existing_fences = Fence.query.filter_by(prompt_id=prompt.id).count()
            if existing_fences > 0:
                continue

            fence = Fence(
                prompt_id=prompt.id,
                name="Content",
                content=prompt.content,
                format=prompt.fence_format or "brackets",
                position=1,
            )
            db.session.add(fence)

            if not prompt.description:
                prompt.description = f"Original content: {prompt.content}"

            prompt.content = ""

            db.session.commit()


if __name__ == "__main__":
    import os

    if os.environ.get("WERKZEUG_RUN_MAIN") is None:
        migrate_prompts()
