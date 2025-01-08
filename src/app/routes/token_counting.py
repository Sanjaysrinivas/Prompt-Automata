"""Token counting routes."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from uuid import UUID

import tiktoken
from flask import Blueprint, current_app, jsonify, render_template, request

from src.app.models.api_endpoint import APIEndpoint
from src.app.models.reference_models import PersistentVariable
from src.app.services.background_processor import TaskPriority, TaskStatus

if TYPE_CHECKING:
    from src.app.services.task_manager import TokenCountingTaskManager

token_counting_bp = Blueprint("token_counting", __name__)


@token_counting_bp.route("/", methods=["GET"])
def token_counter():
    """Render token counting interface."""
    return render_template("token_counting/counter.html")


@token_counting_bp.route("/count", methods=["POST"])
async def count_tokens():
    """Submit token counting task."""
    data = request.get_json()
    references = data.get("references", [])
    priority = TaskPriority[data.get("priority", "MEDIUM")]

    task_manager: TokenCountingTaskManager = current_app.token_task_manager
    task_id = await task_manager.count_tokens_async(references, priority)

    return jsonify({"task_id": str(task_id)})


@token_counting_bp.route("/count_text", methods=["POST"])
def count_text():
    """Count tokens in text using tiktoken."""
    try:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"status": "error", "message": "No text provided"}), 400

        text = data["text"]
        encoding = tiktoken.get_encoding("cl100k_base")
        token_count = len(encoding.encode(text))

        return jsonify({"status": "success", "token_count": token_count})
    except Exception as e:
        current_app.logger.error(f"Error counting tokens: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@token_counting_bp.route("/tokens/reference-count", methods=["POST"])
async def count_reference_tokens():
    """Count tokens for a specific reference."""
    data = request.get_json()
    reference = data.get("reference", "")
    current_app.logger.info(f"Received reference count request for: {reference}")

    try:
        if (
            not reference
            or not reference.startswith("@[")
            or not reference.endswith("]")
        ):
            raise ValueError("Invalid reference format")

        ref_content = reference[2:-1]
        ref_type, ref_value = ref_content.split(":", 1)
        current_app.logger.info(
            f"Parsed reference - type: {ref_type}, value: {ref_value}"
        )

        if ref_type not in ["api", "var", "file", "github"]:
            raise ValueError(f"Invalid reference type: {ref_type}")

        content = None
        if ref_type == "var":
            current_app.logger.info(f"Looking up variable: {ref_value}")
            variable = PersistentVariable.query.filter_by(name=ref_value).first()
            if not variable:
                current_app.logger.error(f"Variable not found: {ref_value}")
                raise ValueError(f"Variable not found: {ref_value}")
            content = variable.value
            current_app.logger.info(f"Found variable value: {content}")
        elif ref_type == "api":
            current_app.logger.info(f"Looking up API endpoint: {ref_value}")
            endpoint = APIEndpoint.query.filter_by(name=ref_value).first()
            if not endpoint:
                current_app.logger.error(f"API endpoint not found: {ref_value}")
                raise ValueError(f"API endpoint not found: {ref_value}")
            content = (
                endpoint.content
                if endpoint.content
                else endpoint.description or endpoint.name
            )
            current_app.logger.info(f"Found API endpoint content: {content}")
        elif ref_type == "file":
            file_path = ref_value
            if not os.path.exists(file_path):
                raise ValueError(f"File not found: {file_path}")
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            current_app.logger.info(f"Read file content from: {file_path}")
        elif ref_type == "github":
            if ref_value.startswith("issue:"):
                issue_ref = ref_value.split(":", 1)[1]
                current_app.logger.info(f"Looking up GitHub issue: {issue_ref}")

                try:
                    if "#" not in issue_ref:
                        raise ValueError(
                            "Invalid GitHub issue reference format. Expected: owner/repo#issue"
                        )
                    repo_part, issue_number = issue_ref.split("#", 1)
                    owner, repo = repo_part.split("/", 1)
                except ValueError:
                    raise ValueError(
                        "Invalid GitHub issue reference format. Expected: owner/repo#issue"
                    )

                current_app.logger.info(
                    f"Parsed GitHub reference - owner: {owner}, repo: {repo}, issue: {issue_number}"
                )

                endpoint = APIEndpoint.query.filter_by(type="github").first()
                if not endpoint:
                    current_app.logger.error("GitHub API endpoint not configured")
                    raise ValueError("GitHub API endpoint not configured")

                handler = GitHubAPIHandler(endpoint)
                issue_data = await handler.get_issue_content(owner, repo, issue_number)
                if issue_data is None:
                    raise ValueError(
                        f"GitHub issue not found: {owner}/{repo}#{issue_number}"
                    )

                content = (
                    f"{issue_data.get('title', '')}\n\n{issue_data.get('body', '')}"
                )
            else:
                raise ValueError(f"Invalid GitHub reference format: {ref_value}")

        if content is None:
            raise ValueError("Failed to get reference content")

        token_service = current_app.token_service
        token_count, _ = await token_service.count_tokens(content)
        current_app.logger.info(f"Token count for {reference} content: {token_count}")

        return jsonify(
            {"status": "success", "token_count": token_count, "reference": reference}
        )
    except ValueError as e:
        current_app.logger.error(f"ValueError in reference counting: {e!s}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error in reference counting: {e!s}")
        return jsonify(
            {"status": "error", "message": f"Failed to count tokens: {e!s}"}
        ), 500


@token_counting_bp.route("/status/<task_id>", methods=["GET"])
def get_task_status(task_id: str):
    """Get task status."""
    task_manager: TokenCountingTaskManager = current_app.token_task_manager
    task = task_manager.processor.get_task(UUID(task_id))

    if not task:
        return jsonify({"error": "Task not found"}), 404

    response = {
        "status": task.status.value,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }

    if task.status == TaskStatus.COMPLETED:
        response["result"] = task.result
    elif task.status == TaskStatus.FAILED:
        response["error"] = str(task.error)

    return jsonify(response)


@token_counting_bp.route("/api/validate_path", methods=["POST"])
def validate_path():
    try:
        data = request.get_json()
        if not data or "path" not in data:
            return jsonify({"valid": False, "message": "No path provided"}), 400

        path = data["path"]

        allowed_dirs = [
            os.path.abspath("prompts"),
            os.path.abspath("tests"),
            os.path.abspath("examples"),
        ]

        abs_path = os.path.abspath(path)

        is_valid = any(
            os.path.commonpath([abs_path, allowed_dir]) == allowed_dir
            for allowed_dir in allowed_dirs
        )

        return jsonify(
            {
                "valid": is_valid,
                "message": "File path is valid"
                if is_valid
                else "File path is not in allowed directory",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error validating path: {e!s}")
        return jsonify({"valid": False, "message": str(e)}), 500
