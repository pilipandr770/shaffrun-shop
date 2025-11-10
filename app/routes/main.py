import io

from flask import Blueprint, Response, abort, current_app, render_template, send_file

from app.models import BlogPost, Document, Product

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(3).all()
    products = (
        Product.query.filter_by(is_available=True)
        .order_by(Product.created_at.desc())
        .limit(4)
        .all()
    )
    return render_template(
        "index.html",
        posts=posts,
        products=products,
        page_title="Discover Voloskyi Saffron",
        page_description="Premium saffron products, educational resources, and daily insights from Voloskyi Saffron.",
    )


@bp.route("/about")
def about():
    return render_template(
        "about.html",
        page_title="About Voloskyi Saffron",
        page_description="Learn about Voloskyi Saffron's heritage, sustainability practices, and mission.",
    )


@bp.route("/documents")
def documents():
    docs = Document.query.order_by(Document.uploaded_at.desc()).all()
    return render_template(
        "documents.html",
        docs=docs,
        page_title="Certificates & Documents",
        page_description="Download quality certificates, product specifications, and company documents.",
    )


@bp.route("/blog")
def blog_list():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template(
        "blog/list.html",
        posts=posts,
        page_title="Saffron Insights",
        page_description="Fresh stories and guides from the Voloskyi Saffron blog.",
    )


@bp.route("/blog/<int:post_id>")
def blog_detail(post_id: int):
    post = BlogPost.query.get_or_404(post_id)
    return render_template(
        "blog/detail.html",
        post=post,
        page_title=post.title,
        page_description=post.content[:155] if post.content else "Saffron inspiration.",
    )


@bp.route("/blog/<int:post_id>/image")
def blog_image(post_id: int):
    post = BlogPost.query.get_or_404(post_id)
    if not post.image_data:
        abort(404)

    return send_file(
        io.BytesIO(post.image_data),
        mimetype=post.image_mimetype or "image/jpeg",
        download_name=post.image_filename or f"blog-{post_id}.jpg",
    )


@bp.route("/robots.txt")
def robots() -> Response:
    base_url = current_app.config.get("BASE_URL", "").rstrip("/")
    lines = [
        "User-agent: *",
        "Allow: /",
    ]
    if base_url:
        lines.append(f"Sitemap: {base_url}/sitemap.xml")
    content = "\n".join(lines) + "\n"
    return Response(content, mimetype="text/plain")
