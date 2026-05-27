"""Flask blueprint for auth pages."""
from __future__ import annotations

from pathlib import Path

import flask

from src import auth as A

_TEMPLATES = Path(__file__).resolve().parent / "templates"

auth_bp = flask.Blueprint(
    "auth",
    __name__,
    url_prefix="/auth",
    template_folder=str(_TEMPLATES),
)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if flask.request.method == "POST":
        email = flask.request.form.get("email", "").strip().lower()
        password = flask.request.form.get("password", "")
        display_name = flask.request.form.get("display_name", "").strip()
        if not (email and password and display_name):
            flask.flash("All fields are required.", "error")
            return flask.render_template("auth/signup.html")
        if len(password) < 8:
            flask.flash("Password must be at least 8 characters.", "error")
            return flask.render_template("auth/signup.html")
        try:
            A.sign_up(email, password, display_name)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Signup failed: {e}", "error")
            return flask.render_template("auth/signup.html")
        return flask.render_template(
            "auth/check_email.html",
            message="Check your inbox for a confirmation link.",
        )
    return flask.render_template("auth/signup.html")


# Stub routes — replaced with real implementations in Tasks 9 and 10.
# These exist now so `url_for('auth.callback', _external=True)` in
# `src/auth.py::_callback_url` resolves during this task's tests.
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if flask.request.method == "POST":
        email = flask.request.form.get("email", "").strip().lower()
        password = flask.request.form.get("password", "")
        if not (email and password):
            flask.flash("Email and password are required.", "error")
            return flask.render_template("auth/login.html")
        try:
            A.sign_in(email, password)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Login failed: {e}", "error")
            return flask.render_template("auth/login.html")
        return flask.redirect("/")
    return flask.render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    A.sign_out()
    return flask.redirect("/")


@auth_bp.route("/forgot", methods=["GET", "POST"])
def forgot():
    if flask.request.method == "POST":
        email = flask.request.form.get("email", "").strip().lower()
        if not email:
            flask.flash("Email is required.", "error")
            return flask.render_template("auth/forgot.html")
        try:
            A.request_password_reset(email)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Could not send reset email: {e}", "error")
            return flask.render_template("auth/forgot.html")
        return flask.render_template(
            "auth/check_email.html",
            message="If that email is registered, we just sent a reset link.",
        )
    return flask.render_template("auth/forgot.html")


@auth_bp.route("/reset", methods=["GET", "POST"])
def reset():
    if not A.current_user_id():
        flask.flash("Open the reset link from your email first.", "error")
        return flask.redirect(flask.url_for("auth.forgot"))
    if flask.request.method == "POST":
        new = flask.request.form.get("password", "")
        if len(new) < 8:
            flask.flash("Password must be at least 8 characters.", "error")
            return flask.render_template("auth/reset.html")
        try:
            A.update_password(new)
        except Exception as e:  # noqa: BLE001
            flask.flash(f"Could not update password: {e}", "error")
            return flask.render_template("auth/reset.html")
        flask.flash("Password updated.", "info")
        return flask.redirect("/")
    return flask.render_template("auth/reset.html")


@auth_bp.route("/callback")
def callback():
    code = flask.request.args.get("code")
    if not code:
        flask.flash("Missing confirmation code.", "error")
        return flask.redirect(flask.url_for("auth.login"))
    try:
        A.exchange_code_for_session(code)
    except Exception as e:  # noqa: BLE001
        flask.flash(f"Could not complete login: {e}", "error")
        return flask.redirect(flask.url_for("auth.login"))
    nxt = flask.request.args.get("next") or "/"
    return flask.redirect(nxt)
