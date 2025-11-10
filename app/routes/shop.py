import io
import os

import stripe
from flask import (Blueprint, abort, current_app, redirect, render_template,
                   request, send_file, url_for)

from app import db
from app.models import Category, Product

bp = Blueprint("shop", __name__, url_prefix="/shop")


def _init_stripe() -> None:
    api_key = current_app.config.get("STRIPE_SECRET_KEY") or os.getenv("STRIPE_SECRET_KEY")
    if not api_key:
        raise RuntimeError("Stripe secret key is not configured.")
    stripe.api_key = api_key


@bp.route("/")
def catalog():
    categories = Category.query.order_by(Category.name.asc()).all()
    products = Product.query.filter_by(is_available=True).order_by(Product.created_at.desc()).all()
    return render_template(
        "shop/catalog.html",
        categories=categories,
        products=products,
        page_title="Shop Saffron",
        page_description="Explore Voloskyi Saffron products, curated by category and crafted for culinary excellence.",
    )


@bp.route("/category/<int:category_id>")
def category(category_id: int):
    cat = Category.query.get_or_404(category_id)
    return render_template(
        "shop/category.html",
        cat=cat,
        page_title=f"{cat.name} Products",
        page_description=cat.description or "Browse premium saffron selections by category.",
    )


@bp.route("/product/<int:product_id>")
def product(product_id: int):
    product_obj = Product.query.get_or_404(product_id)
    related = (
        Product.query.filter(
            Product.category_id == product_obj.category_id,
            Product.id != product_obj.id,
            Product.is_available == True,  # noqa: E712 - expressive equality check
        )
        .limit(3)
        .all()
        if product_obj.category_id
        else []
    )
    return render_template(
        "shop/product.html",
        p=product_obj,
        related=related,
        page_title=product_obj.title,
        page_description=product_obj.description[:155] if product_obj.description else "Saffron offering.",
    )


@bp.route("/product/<int:product_id>/image")
def product_image(product_id: int):
    product_obj = Product.query.get_or_404(product_id)
    if not product_obj.image_data:
        abort(404)

    return send_file(
        io.BytesIO(product_obj.image_data),
        mimetype=product_obj.image_mimetype or "image/jpeg",
        download_name=product_obj.image_filename or f"product-{product_id}.jpg",
    )


@bp.route("/search")
def search():
    query = request.args.get("q", "").strip()
    results = []
    if query:
        like_pattern = f"%{query.lower()}%"
        results = (
            Product.query.filter(
                Product.is_available == True,  # noqa: E712 - expressive equality check
                db.func.lower(Product.title).like(like_pattern),
            )
            .order_by(Product.created_at.desc())
            .all()
        )
    return render_template(
        "shop/search.html",
        query=query,
        results=results,
        page_title="Search Products",
        page_description="Find Voloskyi Saffron products by name or keyword.",
    )


@bp.route("/checkout/<int:product_id>")
def checkout(product_id: int):
    product_obj = Product.query.get_or_404(product_id)
    _init_stripe()

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price_data": {
                    "currency": "eur",
                    "product_data": {"name": product_obj.title},
                    "unit_amount": int(product_obj.price * 100),
                },
                "quantity": 1,
            }
        ],
        mode="payment",
        success_url=url_for("shop.success", _external=True),
        cancel_url=url_for("shop.cancel", _external=True),
    )
    return redirect(session.url, code=303)


@bp.route("/success")
def success():
    return render_template(
        "shop/success.html",
        page_title="Payment Successful",
        page_description="Thank you for shopping with Voloskyi Saffron.",
    )


@bp.route("/cancel")
def cancel():
    return render_template(
        "shop/cancel.html",
        page_title="Payment Cancelled",
        page_description="Your checkout was cancelled. Continue exploring saffron essentials.",
    )
