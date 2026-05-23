from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        usuario = session.get("usuario")

        if not usuario:
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("auth.login"))

        if not usuario.get("ativo", True):
            session.pop("usuario", None)
            flash("Usuário sem acesso ativo.", "danger")
            return redirect(url_for("auth.login"))

        return func(*args, **kwargs)
    return wrapper


def perfil_required(*perfis_permitidos):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            usuario = session.get("usuario")

            if not usuario:
                flash("Faça login para continuar.", "warning")
                return redirect(url_for("auth.login"))

            perfil_usuario = (usuario.get("perfil") or "").strip().upper()
            perfis = [(p or "").strip().upper() for p in perfis_permitidos]

            if perfil_usuario not in perfis:
                flash("Você não tem permissão para acessar esta área.", "danger")
                return redirect(url_for("home.index"))

            return func(*args, **kwargs)
        return wrapper
    return decorator