from typing import Optional, Tuple

from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app import db
from app.models import BlogPost, Category, Document, Product, User
from app.utils import trigger_blog_post_generation

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _get_category_options():
    return Category.query.order_by(Category.name.asc()).all()


MAX_IMAGE_BYTES = 3 * 1024 * 1024
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def _extract_image_payload(upload: FileStorage) -> Tuple[bytes, str, str] | Tuple[None, None, None]:
    if not upload or not upload.filename:
        return None, None, None

    payload = upload.read()
    if not payload:
        return None, None, None

    if len(payload) > MAX_IMAGE_BYTES:
        flash("Image file is too large (max 3MB).", "warning")
        return None, None, None

    mimetype = upload.mimetype or "application/octet-stream"
    if not mimetype.startswith("image/"):
        flash("Only image uploads are allowed.", "warning")
        return None, None, None

    return payload, mimetype, secure_filename(upload.filename)


@bp.route("/setup", methods=["GET", "POST"])
def setup_admin():
    if User.query.first():
        flash("Administrator already configured. Please sign in.", "info")
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("admin/setup.html")
        user = User(email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Administrator created. Please sign in.", "success")
        return redirect(url_for("admin.login"))
    return render_template("admin/setup.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user: Optional[User] = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials. Please try again.", "danger")
    return render_template("admin/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out successfully.", "success")
    return redirect(url_for("admin.login"))


@bp.route("/")
@login_required
def dashboard():
    stats = {
        "products": Product.query.count(),
        "categories": Category.query.count(),
        "blog_posts": BlogPost.query.count(),
        "documents": Document.query.count(),
    }
    latest_orders = Product.query.order_by(Product.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, latest_products=latest_orders)


@bp.route("/products")
@login_required
def products():
    items = Product.query.order_by(Product.created_at.desc()).all()
    return render_template("admin/products.html", products=items)


@bp.route("/products/add", methods=["GET", "POST"])
@login_required
def add_product():
    categories = _get_category_options()
    if request.method == "POST":
        form = request.form
        category_value = form.get("category_id") or None
        product = Product(
            title=form.get("title", "").strip(),
            description=form.get("description", ""),
            price=float(form.get("price", 0) or 0),
            is_available=form.get("is_available") == "on",
            category_id=int(category_value) if category_value else None,
        )
        upload = request.files.get("image")
        image_data, image_mimetype, image_filename = _extract_image_payload(upload)
        if image_data:
            product.image_data = image_data
            product.image_mimetype = image_mimetype
            product.image_filename = image_filename
        db.session.add(product)
        db.session.commit()
        flash("Product created successfully.", "success")
        return redirect(url_for("admin.products"))
    return render_template("admin/add_product.html", categories=categories)


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    categories = _get_category_options()
    if request.method == "POST":
        form = request.form
        product.title = form.get("title", "").strip()
        product.description = form.get("description", "")
        product.price = float(form.get("price", 0) or 0)
        product.is_available = form.get("is_available") == "on"
        category_value = form.get("category_id") or None
        product.category_id = int(category_value) if category_value else None
        if form.get("remove_image") == "on":
            product.image_data = None
            product.image_mimetype = None
            product.image_filename = None
        upload = request.files.get("image")
        image_data, image_mimetype, image_filename = _extract_image_payload(upload)
        if image_data:
            product.image_data = image_data
            product.image_mimetype = image_mimetype
            product.image_filename = image_filename
        db.session.commit()
        flash("Product updated.", "success")
        return redirect(url_for("admin.products"))
    return render_template("admin/edit_product.html", product=product, categories=categories)


@bp.route("/products/<int:product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id: int):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash("Product removed.", "success")
    return redirect(url_for("admin.products"))


@bp.route("/categories", methods=["GET", "POST"])
@login_required
def categories():
    if request.method == "POST":
        form = request.form
        category = Category(
            name=form.get("name", "").strip(),
            description=form.get("description", ""),
        )
        db.session.add(category)
        db.session.commit()
        flash("Category saved.", "success")
        return redirect(url_for("admin.categories"))
    items = Category.query.order_by(Category.created_at.desc()).all()
    return render_template("admin/categories.html", categories=items)


@bp.route("/categories/<int:category_id>/delete", methods=["POST"])
@login_required
def delete_category(category_id: int):
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash("Category deleted.", "success")
    return redirect(url_for("admin.categories"))


@bp.route("/blog", methods=["GET", "POST"])
@login_required
def blog_posts():
    if request.method == "POST":
        form = request.form
        post = BlogPost(
            title=form.get("title", "").strip(),
            content=form.get("content", ""),
        )
        upload = request.files.get("image")
        image_data, image_mimetype, image_filename = _extract_image_payload(upload)
        if image_data:
            post.image_data = image_data
            post.image_mimetype = image_mimetype
            post.image_filename = image_filename
        db.session.add(post)
        db.session.commit()
        flash("Blog post published.", "success")
        return redirect(url_for("admin.blog_posts"))
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template("admin/blog_posts.html", posts=posts)


@bp.route("/blog/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_blog_post(post_id: int):
    post = BlogPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Blog post removed.", "success")
    return redirect(url_for("admin.blog_posts"))


@bp.route("/blog/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_blog_post(post_id: int):
    post = BlogPost.query.get_or_404(post_id)
    if request.method == "POST":
        form = request.form
        post.title = form.get("title", "").strip()
        post.content = form.get("content", "")
        if form.get("remove_image") == "on":
            post.image_data = None
            post.image_mimetype = None
            post.image_filename = None
        upload = request.files.get("image")
        image_data, image_mimetype, image_filename = _extract_image_payload(upload)
        if image_data:
            post.image_data = image_data
            post.image_mimetype = image_mimetype
            post.image_filename = image_filename
        db.session.commit()
        flash("Blog post updated.", "success")
        return redirect(url_for("admin.blog_posts"))
    return render_template("admin/edit_blog_post.html", post=post)


@bp.route("/blog/generate", methods=["POST"])
@login_required
def generate_blog_post_now():
    app = current_app._get_current_object()
    success = trigger_blog_post_generation(app)
    if success:
        flash("AI-generated blog post published.", "success")
    else:
        flash("AI blog generation failed. Check logs and API key.", "warning")
    return redirect(url_for("admin.blog_posts"))


@bp.route("/documents", methods=["GET", "POST"])
@login_required
def documents_admin():
    if request.method == "POST":
        form = request.form
        upload = request.files.get("file")
        if not upload or not upload.filename:
            flash("Please choose a document to upload.", "warning")
            return redirect(url_for("admin.documents_admin"))

        payload = upload.read()
        if not payload:
            flash("Uploaded document is empty.", "warning")
            return redirect(url_for("admin.documents_admin"))

        if len(payload) > MAX_DOCUMENT_BYTES:
            flash("Document is too large (max 10MB).", "warning")
            return redirect(url_for("admin.documents_admin"))

        filename = secure_filename(upload.filename) or upload.filename or "document"

        doc = Document(
            title=form.get("title", "").strip(),
            description=form.get("description", ""),
            file_name=filename,
            file_mimetype=upload.mimetype or "application/octet-stream",
            file_data=payload,
        )
        db.session.add(doc)
        db.session.commit()
        flash("Document uploaded.", "success")
        return redirect(url_for("admin.documents_admin"))
    docs = Document.query.order_by(Document.uploaded_at.desc()).all()
    return render_template("admin/documents.html", docs=docs)


@bp.route("/documents/<int:doc_id>/delete", methods=["POST"])
@login_required
def delete_document(doc_id: int):
    doc = Document.query.get_or_404(doc_id)
    db.session.delete(doc)
    db.session.commit()
    flash("Document deleted.", "success")
    return redirect(url_for("admin.documents_admin"))
