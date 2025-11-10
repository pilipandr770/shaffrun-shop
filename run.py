from app import create_app, db

app = create_app()


@app.shell_context_processor
def make_shell_context():
    from app.models import BlogPost, Category, Document, Product, User

    return {
        "db": db,
        "User": User,
        "Category": Category,
        "Product": Product,
        "BlogPost": BlogPost,
        "Document": Document,
    }


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
