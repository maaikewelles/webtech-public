from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user as flask_login_user,
    logout_user as flask_logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash

from core import (
    as_app_user,
    get_db,
    get_preferred_form,
    get_user_by_email,
    get_user_by_id,
    normalize_email,
)


bp = Blueprint("auth", __name__)


@bp.route("/auth", methods=["GET", "POST"])
def auth() -> str:
    # het afhandelen van login en registratie in één route zodat de template tussen beide formulieren kan schakelen
    message = None
    preferred_form = get_preferred_form(request.args.get("form", "login"))

    if request.method == "GET" and current_user.is_authenticated:
        message = f"Je bent ingelogd als {current_user.email}."

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "login":
            email = normalize_email(request.form.get("email", ""))
            password = request.form.get("password", "")

            if not email or not password:
                message = "Vul je e-mailadres en wachtwoord in."
                preferred_form = "login"
            else:
                user = get_user_by_email(email)
                if user and check_password_hash(user["password_hash"], password):
                    is_first_login = user["last_login"] is None
                    auth_user = as_app_user(user)
                    if auth_user is not None:
                        flask_login_user(auth_user)
                        if is_first_login:
                            flash(f"Welkom {auth_user.name}! Je account is succesvol geregistreerd.", "success")
                        else:
                            flash(f"Welkom terug, {auth_user.name}! Fijn dat je er weer bent.", "success")
                        db = get_db()
                        db.execute(
                            "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                            (auth_user.id,),
                        )
                        db.commit()
                    return redirect(url_for("account.profile"))

                message = "Onjuist e-mailadres of wachtwoord."
                preferred_form = "login"

        elif form_type == "register":
            name = request.form.get("name", "").strip()
            email = normalize_email(request.form.get("email", ""))
            password = request.form.get("password", "")

            if len(name) < 2:
                message = "Vul een geldige naam in."
                preferred_form = "register"
            elif not email:
                message = "Vul een geldig e-mailadres in."
                preferred_form = "register"
            elif len(password) < 8:
                message = "Kies een wachtwoord van minimaal 8 tekens."
                preferred_form = "register"
            else:
                db = get_db()
                existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                if existing:
                    message = "Er bestaat al een account met dit e-mailadres."
                    preferred_form = "register"
                else:
                    password_hash = generate_password_hash(password)
                    cursor = db.execute(
                        "INSERT INTO users (name, email, password_hash, is_admin) VALUES (?, ?, ?, 0)",
                        (name, email, password_hash),
                    )
                    db.commit()

                    created_user = get_user_by_id(int(cursor.lastrowid))
                    auth_user = as_app_user(created_user)
                    if auth_user is not None:
                        flask_login_user(auth_user)
                    return redirect(url_for("account.profile"))

    return render_template("auth.html", message=message, preferred_form=preferred_form)


@bp.get("/login")
def login_page() -> str:
    return redirect(url_for("auth.auth", form="login"))


@bp.get("/register")
def register_page() -> str:
    return redirect(url_for("auth.auth", form="register"))


@bp.post("/logout")
@login_required
def logout() -> str:
    flask_logout_user()
    flash("Je bent succesvol uitgelogd. Tot snel bij Hoofdzaken & Co!", "success")
    return redirect(url_for("index"))
