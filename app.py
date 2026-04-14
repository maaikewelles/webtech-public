import os
import secrets
from pathlib import Path

from flask import Flask, abort, render_template, request, session, url_for
from markupsafe import Markup
try:
    from flask_login import LoginManager, current_user
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency: Flask-Login. Use run.bat or run .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
    ) from exc

from core import (
    AppUser,
    as_app_user,
    close_db,
    get_user_by_id,
    init_books_db,
    init_db,
)


def create_app() -> Flask:
    # hier wordt de app geconfigureerd, databases geïnitialiseerd en blueprints geregistreerd voordat de eerste request binnenkomt
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["DATABASE"] = str(Path(app.instance_path) / "users.db")
    app.config["BOOKS_DATABASE"] = str(Path(app.instance_path) / "books.db")
    app.config["UPLOAD_FOLDER"] = str(Path(app.static_folder) / "uploads")
    app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.auth"
    login_manager.login_message = ""

    @login_manager.user_loader
    def load_user(user_id: str) -> AppUser | None:
        try:
            db_user_id = int(user_id)
        except ValueError:
            return None
        return as_app_user(get_user_by_id(db_user_id))

    app.teardown_appcontext(close_db)

    with app.app_context():
        init_db()
        init_books_db()

    from blueprints.account import bp as account_blueprint
    from blueprints.auth import bp as auth_blueprint
    from blueprints.cart import bp as cart_blueprint, get_cart_item_count
    from blueprints.shop import bp as shop_blueprint

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(account_blueprint)
    app.register_blueprint(shop_blueprint)
    app.register_blueprint(cart_blueprint)

    @app.context_processor
    def inject_auth_state():
        return {
            "current_user_name": current_user.name if current_user.is_authenticated else None,
            "current_user_email": current_user.email if current_user.is_authenticated else None,
            "current_user_is_admin": current_user.is_admin if current_user.is_authenticated else False,
        }

    @app.context_processor
    def inject_csrf_token():
        # één CSRF-token per sessie bewaren en gelijk daarvan een hidden form maken
        def csrf_token() -> str:
            token = session.get("csrf_token")
            if not token:
                token = secrets.token_urlsafe(32)
                session["csrf_token"] = token
            return token

        def csrf_field() -> Markup:
            return Markup(f'<input type="hidden" name="csrf_token" value="{csrf_token()}">')

        return {"csrf_token": csrf_token, "csrf_field": csrf_field}

    @app.before_request
    def validate_csrf_token():
        # het verwerpen van POST-verzoeken zonder een geldig sessie-token om formulierinvoer te beveiligen
        if request.method != "POST":
            return None

        session_token = session.get("csrf_token")
        form_token = request.form.get("csrf_token")
        if not session_token or not form_token or form_token != session_token:
            abort(400)

        return None

    @app.context_processor
    def inject_shop_url_builder():
        # het bouwen van shop-linkjes die actieve filters behouden tussen overzichten en productpagina's
        def shop_url(page: int | None = None, book_id: int | None = None, genre: str | None = None, language: str | None = None, price: str | None = None) -> str:
            params = {key: value for key, value in request.args.items() if key in {"genre", "language", "price", "page"} and value}

            if genre is not None:
                if genre == "all":
                    params.pop("genre", None)
                else:
                    params["genre"] = genre
            if language is not None:
                if language == "all":
                    params.pop("language", None)
                else:
                    params["language"] = language
            if price is not None:
                if price == "all":
                    params.pop("price", None)
                else:
                    params["price"] = price

            if page is not None:
                params["page"] = page
            elif book_id is not None:
                params.pop("page", None)

            if book_id is not None:
                return url_for("shop.product_page", book_id=book_id, **params)
            return url_for("shop.shop", **params)

        return {"shop_url": shop_url}

    @app.context_processor
    def inject_cart_state():
        return {"cart_item_count": get_cart_item_count()}

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/contact")
    def contact() -> str:
        return render_template("contact.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
