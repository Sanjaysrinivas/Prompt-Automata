from __future__ import annotations

from src.app import app
from src.app.models.fence import Fence
from src.app.models.prompt import Prompt


def check_prompts():
    with app.app_context():
        prompts = Prompt.query.all()
        for prompt in prompts:
            fences = (
                Fence.query.filter_by(prompt_id=prompt.id)
                .order_by(Fence.position)
                .all()
            )
            for _fence in fences:
                pass


if __name__ == "__main__":
    check_prompts()
