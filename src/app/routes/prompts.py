"""Routes for prompt management."""

from __future__ import annotations

import logging
import os
import re
from http import HTTPStatus
from pathlib import Path

import tiktoken
from flask import (
    Blueprint,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
    session,
)
from flask_login import login_required
from werkzeug.exceptions import BadRequest

from src.app.models.api_endpoint import APIEndpoint
from src.app.models.reference_models import PersistentVariable
from src.app.services.github_api_handler import GitHubAPIHandler
from src.app.services.prompt_handler import FenceFormat
from src.app.services.prompt_service import PromptService
from src.app.validators.base import ValidationError
from src.app.validators.prompt_validators import PromptFenceValidator, PromptValidator

logger = logging.getLogger(__name__)

prompts_bp = Blueprint("prompts", __name__, url_prefix="/prompts")


def _raise_no_data() -> None:
    """Raise BadRequest for missing data."""
    msg = "No data provided"
    raise BadRequest(msg)


def _raise_no_content() -> None:
    """Raise BadRequest for missing content."""
    msg = "No content provided"
    raise BadRequest(msg)


def get_files() -> list[dict]:
    """Get list of files from the workspace."""
    files = []
    workspace = Path(current_app.config.get("WORKSPACE_PATH", Path.cwd())).resolve()

    for file_path in workspace.rglob("*"):
        if file_path.is_file():
            try:
                rel_path = file_path.relative_to(workspace)
                files.append({"name": file_path.name, "path": str(rel_path)})
            except ValueError:
                continue

    return files


def get_fence_formats() -> list[dict]:
    """Get available fence formats for the template."""
    return [
        {"id": format.value, "name": format.name.replace("_", " ").title()}
        for format in FenceFormat
    ]


@prompts_bp.route("/new", methods=["GET"])
def new_prompt() -> str:
    """Render the prompt creation page."""
    files = get_files()
    fence_formats = get_fence_formats()

    return render_template(
        "prompt/editor.html",
        files=files,
        fence_formats=fence_formats,
        admin_token=current_app.config["ADMIN_TOKEN"],
    )


@prompts_bp.route("/<int:prompt_id>", methods=["GET"])
def get_prompt(prompt_id: int) -> tuple[dict, int]:
    """Get a specific prompt."""
    prompt_dict, error = PromptService.get_prompt(prompt_id)
    if error:
        return jsonify({"error": error}), HTTPStatus.NOT_FOUND
    return jsonify(prompt_dict), HTTPStatus.OK


@prompts_bp.route("/", methods=["GET"])
def list_prompts() -> str | tuple[dict, int]:
    """List all prompts."""
    template_only = request.args.get("template_only", "").lower() == "true"
    search_query = request.args.get("q", "")
    tags = request.args.getlist("tags")

    if search_query or tags:
        prompts = PromptService.search_prompts(
            query=search_query, tags=tags, template_only=template_only
        )
        return jsonify({"prompts": prompts}), HTTPStatus.OK

    prompts = PromptService.get_all_prompts(template_only=template_only)
    return render_template("prompt/library.html", prompts=prompts)


@prompts_bp.route("/create", methods=["POST"])
async def create_prompt() -> tuple[dict, int]:
    """Create a new prompt."""
    if not request.is_json:
        _raise_no_data()

    data = request.get_json()
    if not data:
        _raise_no_data()

    validator = PromptValidator()
    try:
        validator.validate(data)
    except ValidationError as e:
        return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

    prompt_service = PromptService()
    try:
        prompt_dict, error = await prompt_service.create_prompt(
            title=data["title"],
            content=data.get("content", ""),
            description=data.get("description"),
            tags=data.get("tags", []),
            is_template=data.get("is_template", False),
            provider=data.get("provider"),
            model=data.get("model"),
            fences=data.get("fences", []),
        )

        if error:
            return jsonify({"error": error}), HTTPStatus.BAD_REQUEST

        return jsonify(
            {
                "message": "Prompt created successfully",
                "id": prompt_dict["id"],
                "redirect": f"/prompts/generate/{prompt_dict['id']}",
            }
        ), HTTPStatus.CREATED
    except Exception as e:
        logger.exception("Error creating prompt")
        return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


@prompts_bp.route("/<int:prompt_id>", methods=["PUT"])
def update_prompt(prompt_id: int) -> tuple[dict, int]:
    """Update an existing prompt."""
    data = request.get_json()
    if not data:
        _raise_no_data()

    if "title" in data and not data["title"]:
        return jsonify({"error": "Title is required"}), HTTPStatus.BAD_REQUEST

    fence_validator = PromptFenceValidator()
    prompt_validator = PromptValidator()

    if "fences" in data:
        try:
            fence_validator.validate(data.get("fences", []))
        except Exception as e:
            return jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

        content = "\n".join(
            f"<{fence['name']}>\n{fence['content']}\n</{fence['name']}>"
            for fence in data["fences"]
        )
        data["content"] = content

    if "is_template" in data:
        data["is_template"] = bool(data["is_template"])

    if "tags" in data and isinstance(data["tags"], list):
        data["tags"] = ",".join(data["tags"])

    prompt_dict, error = PromptService.update_prompt(
        prompt_id,
        fences=data.get("fences"),
        **{
            k: v
            for k, v in data.items()
            if k
            in [
                "title",
                "content",
                "description",
                "tags",
                "is_template",
            ]
        },
    )

    if error:
        return jsonify({"error": error}), HTTPStatus.BAD_REQUEST
    return jsonify(prompt_dict), HTTPStatus.OK


@prompts_bp.route("/<int:prompt_id>", methods=["DELETE"])
def delete_prompt(prompt_id: int) -> tuple[dict, int]:
    """Delete a prompt."""
    success, error = PromptService.delete_prompt(prompt_id)
    if error:
        return jsonify({"error": error}), HTTPStatus.NOT_FOUND
    return jsonify({"message": "Prompt deleted successfully"}), HTTPStatus.OK


def format_fence_content(content, fence_format, fence_name):
    """Format fence content based on the fence type."""
    if not content:
        return ""

    content = content.strip()

    if fence_format == "xml_tags":
        return f"<{fence_name}>\n{content}\n</{fence_name}>"

    if fence_format == "triple_quotes":
        return f'{fence_name}\n"""\n{content}\n"""'

    if fence_format == "markdown":
        return f"```\n{content}\n```"

    if fence_format == "curly_braces":
        return f"{fence_name}\n{{\n{content}\n}}"

    return content


@prompts_bp.route("/preview", methods=["POST"])
async def preview_prompt():
    """Preview a prompt with its fences."""
    if not request.is_json:
        _raise_no_data()

    content = request.json.get("content")
    is_native_picker = request.json.get("isNativePicker", False)

    if not content:
        _raise_no_content()

    try:
        # Extract file path from content
        match = re.match(r"@\[file:(.*?)\]", content)
        if match:
            file_path = match.group(1)
            raw_content, error = await get_reference_content(
                "file", file_path, is_native_picker=is_native_picker
            )
            if error:
                return jsonify({"error": error}), HTTPStatus.BAD_REQUEST

            # Format content with fence tags and return as raw text
            formatted_content = f"<fence>\n{raw_content}\n</fence>"
            return formatted_content, HTTPStatus.OK, {"Content-Type": "text/plain"}

        # Find all references in the content
        ref_pattern = r"@\[(\w+):([^\]]+)\]"
        matches = list(re.finditer(ref_pattern, content))
        references = {}

        resolved_content = content
        for match in matches:
            ref_type = match.group(1)
            ref_value = match.group(2).strip()
            ref_content, error = await get_reference_content(ref_type, ref_value)
            if error:
                return jsonify({"error": error}), HTTPStatus.BAD_REQUEST

            resolved_content = resolved_content.replace(match.group(0), ref_content)

        formatted_content = format_fence_content(resolved_content, "", "")

    except Exception:
        current_app.logger.exception("Error in preview_prompt: {e!s}")
        return jsonify(
            {"error": "Error in preview_prompt"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR
    return formatted_content, HTTPStatus.OK, {"Content-Type": "text/plain"}


@prompts_bp.route("/<int:prompt_id>/edit", methods=["GET"])
def edit_prompt_page(prompt_id: int) -> str:
    """Render the prompt edit page."""
    prompt_dict, error = PromptService.get_prompt(prompt_id)
    if error:
        return render_template("error.html", error=error), HTTPStatus.NOT_FOUND

    files = get_files()
    fence_formats = get_fence_formats()

    return render_template(
        "prompt/editor.html",
        prompt=prompt_dict,
        files=files,
        fence_formats=fence_formats,
        admin_token=current_app.config["ADMIN_TOKEN"],
    )


@prompts_bp.route("/generate/<int:prompt_id>")
def generate_prompt_page(prompt_id: int):
    """Render the prompt generation page."""
    logger.info("Rendering generate page for prompt_id: {prompt_id}")
    prompt_dict, error = PromptService.get_prompt(prompt_id)

    if error:
        logger.error("Error getting prompt: {error}")
        return jsonify({"error": error}), HTTPStatus.NOT_FOUND

    logger.info("Retrieved prompt data: {prompt_dict}")
    return render_template(
        "prompt/generate.html", prompt=prompt_dict, title="Generate Prompt"
    )


@prompts_bp.route("/fence-template")
def get_fence_template():
    """Return the fence block template HTML."""
    position = request.args.get("position", 0)
    return render_template("components/editor/fence_block.html", position=position)


def count_tokens_local(text):
    """Count tokens using local tiktoken without any API calls."""
    if not text:
        return 0
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
    except Exception:
        return len(text.split()) if text else 0


@prompts_bp.route("/api/tokens/count", methods=["POST"])
async def count_tokens():
    """Count tokens in text and references."""
    try:
        data = request.get_json()

        if not data or "text" not in data:
            return jsonify({"error": "No text provided"}), 400

        text = data["text"]
        encoding = tiktoken.get_encoding("cl100k_base")

        ref_pattern = r"@\[(\w+):([^\]]+)\]"
        content_only = re.sub(ref_pattern, "", text)

        content_tokens = len(encoding.encode(content_only))

        references = {}
        total_ref_tokens = 0

        for match in re.finditer(ref_pattern, text):
            ref = match.group(0).strip()

            if ":" not in ref:
                references[ref] = 0
                continue

            ref_type, ref_value = ref.split(":", 1)
            ref_type = ref_type.strip().lower()
            ref_value = ref_value.strip()

            content = await get_reference_content(ref_type, ref_value)

            if content is None:
                references[ref] = 0
                continue

            if not isinstance(content, str):
                references[ref] = 0
                continue

            try:
                ref_tokens = len(encoding.encode(content))
                references[ref] = ref_tokens
                total_ref_tokens += ref_tokens
            except Exception:
                references[ref] = 0

        return jsonify(
            {
                "content_tokens": content_tokens,
                "reference_tokens": total_ref_tokens,
                "total_tokens": content_tokens + total_ref_tokens,
                "references": references,
                "success": True,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


@prompts_bp.route("/api/tokens/reference-count", methods=["POST"])
async def count_reference_tokens():
    """Count tokens in a reference."""
    try:
        data = request.get_json()
        if not data or "reference" not in data:
            return jsonify({"error": "No reference provided"}), 400

        reference = data["reference"]
        token_count = count_tokens_local(reference)

        return jsonify({"token_count": token_count, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500


def format_directory_tree(
    path: Path, prefix: str = "", is_last: bool = True
) -> list[str]:
    """Format directory contents as an ASCII tree.

    Args:
        path: Directory path to format
        prefix: Current line prefix for indentation
        is_last: Whether this is the last item in current level

    Returns:
        list[str]: Lines of the tree
    """
    lines = []

    # Add current directory/file
    if path.parent != path:  # Skip root directory name
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{path.name}")

    if path.is_dir():
        # Get all visible items, sorted with directories first
        try:
            items = sorted(
                [p for p in path.iterdir() if not p.name.startswith(".")],
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )

            # Prepare the prefix for children
            child_prefix = prefix + ("    " if is_last else "│   ")

            # Add each child
            for i, item in enumerate(items):
                is_last_item = i == len(items) - 1
                lines.extend(format_directory_tree(item, child_prefix, is_last_item))

        except PermissionError:
            lines.append(f"{prefix}    <Permission denied>")

    return lines


async def get_reference_content(
    reference_type: str, value: str, is_native_picker: bool = False
) -> tuple[str, str | None]:
    """Get the content of a reference.

    Args:
        reference_type: Type of reference (file, url, etc)
        value: Value of reference (file path, url, etc)
        is_native_picker: Whether the file was selected through native file picker

    Returns:
        tuple[str, str | None]: (content, error)
    """
    content = ""
    error = None

    try:
        current_app.logger.info(
            "[Reference Content] Processing reference type: '{reference_type}', value: '{value}'"
        )

        if reference_type == "file":
            # For native file picker, skip workspace directory check
            if not is_path_allowed(Path(value), is_native_picker=is_native_picker):
                return "", f"Path not allowed: {value}"

            file_path = Path(value)
            if file_path.is_file():
                with open(file_path, encoding="utf-8") as file:
                    content = file.read()
                return content, error
            return "", f"File not found: {value}"
        if reference_type == "dir":
            return f"@[dir:{value}]", error
        if reference_type in ["variable", "var"]:
            current_app.logger.info("[Reference Content] Looking up variable")
            all_vars = PersistentVariable.query.all()
            current_app.logger.info("[Reference Content] All variables in database")

            # Try exact match first
            variable = PersistentVariable.query.filter_by(name=value).first()

            if not variable:
                # Try with stripped whitespace
                variable = next(
                    (v for v in all_vars if v.name.strip() == value.strip()), error
                )

            if not variable:
                # Try case-insensitive match
                variable = PersistentVariable.query.filter(
                    PersistentVariable.name.ilike(value)
                ).first()

            if not variable:
                # Try matching with different space variations
                cleaned_value = value.replace(" ", "").lower()
                variable = next(
                    (
                        v
                        for v in all_vars
                        if v.name.replace(" ", "").lower() == cleaned_value
                    ),
                    error,
                )

            if variable:
                current_app.logger.info(
                    "[Reference Content] Found variable '{variable.name}' with value"
                )
                return variable.value

            current_app.logger.error("[Reference Content] Variable not found")
            return error

        if reference_type == "github":
            if value.startswith("issue:"):
                issue_ref = value.split(":", 1)[1]
                try:
                    if "#" not in issue_ref:
                        msg = "Invalid GitHub issue reference format. Expected: owner/repo#issue"
                        raise ValueError(msg)
                    repo_part, issue_number = issue_ref.split("#", 1)
                    owner, repo = repo_part.split("/", 1)
                except ValueError:
                    return (
                        "",
                        "Invalid GitHub issue reference format. Expected: owner/repo#issue",
                    )

                endpoint = APIEndpoint.query.filter_by(type="github").first()
                if not endpoint:
                    return "", "GitHub API endpoint not configured"

                handler = GitHubAPIHandler(endpoint)
                try:
                    issue_data = await handler.get_issue_content(
                        owner, repo, issue_number
                    )
                    if issue_data is error:
                        return (
                            "",
                            f"GitHub issue not found: {owner}/{repo}#{issue_number}",
                        )

                    content = f"Issue #{issue_number}: {issue_data.get('title', '')}\n\n{issue_data.get('body', '')}"
                    return content, error
                except Exception as e:
                    return "", f"Error retrieving GitHub issue: {e}"
            return "", f"Unsupported reference type: {reference_type}"

    except Exception as e:
        return "", str(e)


async def resolve_references(content: str) -> str:
    """Helper function to resolve all references in content.

    Args:
        content: Content containing references to resolve

    Returns:
        str: Content with resolved references
    """
    import re

    # Match @[type:value] format
    ref_pattern = r"@\[(\w+):([^\]]+)\]"
    matches = list(re.finditer(ref_pattern, content))

    resolved_content = content
    for match in matches:
        try:
            ref_type = match.group(1)
            ref_value = match.group(2).strip()

            current_app.logger.debug(
                "Resolving reference",
                extra={
                    "ref_type": ref_type,
                    "ref_value": "***REDACTED***",
                    "action": "resolve_reference",
                },
            )

            ref_content, error = await get_reference_content(ref_type, ref_value)
            if error:
                msg = f"Failed to resolve reference {ref_type}:{ref_value}: {error}"
                raise ValueError(msg)

            resolved_content = resolved_content.replace(match.group(0), ref_content)

        except ValueError as e:
            current_app.logger.exception(
                "Reference resolution failed",
                extra={
                    "ref_type": ref_type,
                    "error": str(e),
                    "action": "resolve_reference",
                },
            )
            raise
        except Exception as e:
            current_app.logger.exception(
                "Unexpected error resolving reference",
                extra={"ref_type": ref_type, "action": "resolve_reference"},
            )
            msg = f"Unexpected error resolving reference {ref_type}:{ref_value}: {e!s}"
            raise ValueError(msg)

    return resolved_content


@prompts_bp.route("/api/references/<type>", methods=["GET"])
async def get_reference_options(type: str):
    """Get available reference options based on type."""
    try:
        if type == "variable":
            variables = PersistentVariable.query.all()
            options = [
                {
                    "value": var.name,
                    "label": f"{var.name} - {var.description or 'No description'}",
                }
                for var in variables
            ]
            return jsonify({"options": options})

        if type == "api":
            endpoints = APIEndpoint.query.all()
            options = [
                {"value": api.name, "label": f"{api.name} - {api.base_url}"}
                for api in endpoints
            ]
            return jsonify({"options": options})

        return jsonify({"error": "Invalid reference type"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@prompts_bp.route("/api/llm/providers", methods=["GET"])
@login_required
def get_llm_providers():
    """Get the status of all LLM providers' API keys."""
    providers = {
        "openai": {
            "name": "OpenAI",
            "has_token": bool(current_app.config.get("OPENAI_API_KEY")),
        },
        "anthropic": {
            "name": "Anthropic",
            "has_token": bool(current_app.config.get("ANTHROPIC_API_KEY")),
        },
        "google": {
            "name": "Google",
            "has_token": bool(current_app.config.get("GOOGLE_API_KEY")),
        },
    }
    return jsonify({"providers": providers})


@prompts_bp.route("/api/llm/token", methods=["POST"])
async def save_llm_token():
    """Save LLM provider token in the session after validation."""
    if not request.is_json:
        _raise_no_data()

    data = request.get_json()
    provider = data.get("provider")
    token = data.get("token")

    if not provider or not token:
        msg = "Provider and token are required"
        raise BadRequest(msg)

    validation_funcs = {
        "openai": validate_openai_token,
        "anthropic": validate_anthropic_token,
        "google": validate_google_token,
    }

    validator = validation_funcs.get(provider)
    if not validator:
        msg = f"Invalid provider: {provider}"
        raise BadRequest(msg)

    is_valid = await validator(token)
    if not is_valid:
        msg = f"Invalid token for provider: {provider}"
        raise BadRequest(msg)

    provider_config_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }

    config_key = provider_config_map.get(provider)

    current_app.config[config_key] = token

    return jsonify(
        {"message": f"Token validated and saved for {provider}", "status": "success"}
    )


def _validate_request_data(data):
    """Validate the request data for prompt generation."""
    provider = data.get("provider")
    model = data.get("model")
    if not provider or not model:
        logger.error("Provider and model are required")
        return None, (
            jsonify({"error": "Provider and model are required"}),
            HTTPStatus.BAD_REQUEST,
        )
    return (provider, model), None


async def _process_fences(fences):
    """Process and validate fence content."""
    if not isinstance(fences, list) or not fences:
        logger.error("Invalid or empty fences found in prompt")
        return None, "No content found"

    processed_fences = []
    for i, fence in enumerate(fences):
        if not fence.get("content"):
            logger.info(f"Empty content found in fence {i+1}")
            return None, "No content found"

        try:
            resolved_content = await resolve_references(fence["content"])
            processed_fences.append(
                {"name": fence["name"], "content": resolved_content}
            )
            logger.info(
                "Successfully processed fence {i+1}",
                extra={"fence_name": fence["name"], "action": "process_fence"},
            )
        except ValueError as e:
            logger.exception("Failed to process fence {i+1}")
            return None, f"Error in fence '{fence['name']}': {e!s}"

    return processed_fences, None


@prompts_bp.route("/generate/<int:prompt_id>", methods=["POST"])
async def generate_prompt_response(prompt_id: int):
    """Generate a response for a prompt using the specified LLM provider."""
    if not request.is_json or not (data := request.get_json()):
        return _raise_no_data()

    # Validate admin authentication
    if not (admin_token := session.get("admin_token")):
        logger.error("No admin token found in session")
        return jsonify(
            {"error": "Admin authentication required"}
        ), HTTPStatus.UNAUTHORIZED

    # Validate request data
    request_data, error = _validate_request_data(data)
    if error:
        return error
    provider, model = request_data

    try:
        # Get and validate prompt
        prompt_dict, error = PromptService.get_prompt(prompt_id)
        if error:
            logger.error("Error getting prompt")
            return jsonify({"error": error}), HTTPStatus.NOT_FOUND

        # Process fences
        processed_fences, error = await _process_fences(prompt_dict.get("fences", []))
        if error:
            return jsonify({"error": error}), HTTPStatus.BAD_REQUEST

        # Format prompt
        formatted_prompt = "\n".join(
            f"### {fence['name']} ###\n{fence['content']}" for fence in processed_fences
        )

        # Initialize LLM service
        from src.app.services.llm_service import LLMService

        llm_service = LLMService()

        if not (token := session.get(f"{provider}_token")):
            logger.exception("No API token found for provider")
            return jsonify(
                {"error": f"No API token found for provider {provider}"}
            ), HTTPStatus.UNAUTHORIZED

        llm_service.set_token(token)

        # Stream generation
        return Response(
            _generate_stream(llm_service, provider, formatted_prompt),
            mimetype="text/event-stream",
        )

    except Exception:
        logger.exception(
            "Error in generate_prompt_response",
            extra={
                "prompt_id": prompt_id,
                "provider": provider,
                "model": model,
                "action": "generate_response",
            },
        )
        return jsonify(
            {"error": "An unexpected error occurred"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


def _generate_stream(llm_service, provider, formatted_prompt):
    """Generator function for streaming LLM responses."""
    try:
        for chunk in llm_service.generate_stream(provider, formatted_prompt):
            if chunk:
                logger.debug("Sending chunk", extra={"chunk_size": len(chunk)})
                yield f"data: {chunk}\n\n"
    except Exception as e:
        logger.exception("Error during generation")
        yield f"data: Error: {e!s}\n\n"
    finally:
        yield "data: [DONE]\n\n"


async def validate_openai_token(token: str) -> bool:
    """Validate OpenAI API token."""
    try:
        import openai

        openai.api_key = token
        await openai.ChatCompletion.acreate(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "test"}],
            max_tokens=1,
        )

    except Exception:
        logger.exception("OpenAI token validation failed")
        return False

    return True


async def validate_anthropic_token(token: str) -> bool:
    """Validate Anthropic API token."""
    try:
        import anthropic

        client = anthropic.Client(api_key=token)
        await client.messages.create(
            model="claude-2",
            max_tokens=1,
            messages=[{"role": "user", "content": "test"}],
        )

    except Exception:
        logger.exception("Anthropic token validation failed")
        return False

    return True


async def validate_google_token(token: str) -> bool:
    """Validate Google API token."""
    try:
        from litellm import completion

        completion(
            model="gemini-1.5-pro",
            messages=[{"role": "user", "content": "test"}],
            api_key=token,
        )
    except Exception:
        logger.exception("Google token validation failed")
        return False

    return True


def is_path_allowed(path: Path, *, is_native_picker: bool = False) -> bool:
    """Check if a path is allowed.

    Args:
        path: Path to check
        is_native_picker: Whether the file was selected through native file picker
    """
    workspace_path = current_app.config.get(
        "WORKSPACE_PATH", Path(__file__).resolve().parent
    )
    allowed_dirs = current_app.config.get("ALLOWED_DIRS", [workspace_path])

    current_app.logger.info(
        "[Path Check] Checking if {path} is allowed. Is native picker: {is_native_picker}"
    )

    if not is_native_picker:
        for allowed_dir in allowed_dirs:
            allowed_path = Path(allowed_dir).resolve()
            try:
                if path.is_relative_to(allowed_path):
                    current_app.logger.info(
                        "[Path Check] Path {path} is relative to allowed dir {allowed_path}"
                    )
                    return True
            except Exception:
                current_app.logger.exception(
                    "[Path Check] Error checking if {path} is relative to {allowed_path}"
                )
                continue

    if path.is_file():
        has_access = os.access(str(path), os.R_OK)
        current_app.logger.info(
            "[Path Check] File {path} has read access: {has_access}"
        )
        return has_access
    if path.is_dir():
        has_access = os.access(str(path), os.R_OK | os.X_OK)
        current_app.logger.info(
            "[Path Check] Directory {path} has read/execute access: {has_access}"
        )
        return has_access

    current_app.logger.info("[Path Check] File {path} has read access: {has_access}")
    return has_access
