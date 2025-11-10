import os
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify, request
from openai import OpenAI

from app.models import BlogPost, Category, Product

bp = Blueprint("assistant", __name__, url_prefix="/assistant")


def _collect_context() -> Dict[str, Any]:
    products = Product.query.filter_by(is_available=True).all()
    categories = Category.query.order_by(Category.name.asc()).all()
    blog_posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(5).all()

    return {
        "categories": categories,
        "products": products,
        "blog_posts": blog_posts,
    }


def _format_context(context: Dict[str, Any]) -> str:
    category_section = "\n".join(f"- {category.name}: {category.description}" for category in context["categories"])
    product_section = "\n".join(
        f"- {product.title} (EUR {product.price:.2f}) — {product.description[:160]}" for product in context["products"]
    )
    blog_section = "\n".join(
        f"- {post.title} ({post.created_at.strftime('%Y-%m-%d')}): {post.content[:160]}" for post in context["blog_posts"]
    )
    return (
        "You are a sales assistant for Voloskyi Saffron.\n"
        f"Categories:\n{category_section or 'No categories yet.'}\n\n"
        f"Products:\n{product_section or 'No products yet.'}\n\n"
        f"Blog highlights:\n{blog_section or 'No blog posts yet.'}"
    )


def _get_openai_client() -> OpenAI:
    api_key = current_app.config.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")
    return OpenAI(api_key=api_key)


@bp.route("/ask", methods=["POST"])
def ask():
    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    question: str = payload.get("question", "").strip()

    if not question:
        return jsonify({"error": "No question provided."}), 400

    context = _collect_context()
    formatted_context = _format_context(context)

    try:
        client = _get_openai_client()
        system_prompt = current_app.config.get(
            "ASSISTANT_PROMPT", "You are a helpful AI sales assistant for Voloskyi Saffron."
        )
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"{system_prompt}\n\n{formatted_context}\n\nCustomer: {question}\nAssistant:",
        )
        reply = response.output_text
    except Exception as exc:  # pragma: no cover - HTTP surface for users
        current_app.logger.exception("Assistant request failed: %s", exc)
        return jsonify({"error": "Assistant service is unavailable right now."}), 503

    return jsonify({"reply": reply})
