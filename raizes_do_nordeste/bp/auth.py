from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import requests

from services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario"):
        return redirect(url_for("home.index"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        senha = (request.form.get("senha") or "").strip()

        if not email or not senha:
            flash("Informe e-mail e senha.", "danger")
            return render_template("login.html")

        api_key = current_app.config.get("FIREBASE_API_KEY")

        if not api_key or api_key == "COLE_AQUI_SUA_WEB_API_KEY":
            flash("Firebase API KEY não configurada no config.py.", "danger")
            return render_template("login.html")

        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

        payload = {
            "email": email,
            "password": senha,
            "returnSecureToken": True,
        }

        try:
            response = requests.post(url, json=payload, timeout=15)
            data = response.json()

            if response.status_code == 200 and "idToken" in data:
                uid = data.get("localId")
                email_autenticado = (data.get("email") or "").strip().lower()

                usuario_sistema = AuthService.buscar_por_uid(uid)

                if not usuario_sistema:
                    usuario_sistema = AuthService.buscar_por_email(email_autenticado)

                if not usuario_sistema:
                    flash("Usuário autenticado, mas sem cadastro no sistema.", "danger")
                    return render_template("login.html")

                if not usuario_sistema.get("ativo", True):
                    flash("Usuário inativo no sistema.", "danger")
                    return render_template("login.html")

                session["usuario"] = {
                    "uid": uid,
                    "id": usuario_sistema.get("id"),
                    "nome": usuario_sistema.get("nome", "Usuário"),
                    "email": usuario_sistema.get("email", email_autenticado),
                    "perfil": usuario_sistema.get("perfil", "USUARIO"),
                    "ativo": usuario_sistema.get("ativo", True),
                    "id_token": data.get("idToken"),
                    "refresh_token": data.get("refreshToken"),
                }

                flash("Login realizado com sucesso.", "success")
                return redirect(url_for("home.index"))

            codigo_erro = data.get("error", {}).get("message", "")

            mapa_erros = {
                "EMAIL_NOT_FOUND": "E-mail não encontrado.",
                "INVALID_PASSWORD": "Senha inválida.",
                "INVALID_LOGIN_CREDENTIALS": "E-mail ou senha inválidos.",
                "USER_DISABLED": "Usuário desativado.",
                "MISSING_PASSWORD": "Informe a senha.",
                "INVALID_EMAIL": "E-mail inválido.",
            }

            flash(mapa_erros.get(codigo_erro, f"Erro no login: {codigo_erro}"), "danger")

        except Exception as e:
            flash(f"Erro ao conectar com o Firebase Authentication: {str(e)}", "danger")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.pop("usuario", None)
    flash("Logout realizado com sucesso.", "success")
    return redirect(url_for("auth.login"))