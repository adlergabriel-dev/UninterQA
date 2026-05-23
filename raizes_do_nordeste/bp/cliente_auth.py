from functools import wraps

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from services.cliente_auth_service import ClienteAuthService
from services.cliente_pedido_service import ClientePedidoService

bp = Blueprint("cliente_auth", __name__, url_prefix="/cliente")


def login_cliente_obrigatorio(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        cliente = session.get("cliente")
        if not cliente:
            flash("Faça login para acessar a área do cliente.", "warning")
            return redirect(url_for("cliente_auth.login"))
        return view(*args, **kwargs)
    return wrapper


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if session.get("cliente"):
        return redirect(url_for("cliente_auth.home"))

    if request.method == "POST":
        nome = (request.form.get("nome") or "").strip()
        telefone = (request.form.get("telefone") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        cpf = (request.form.get("cpf") or "").strip()
        senha = request.form.get("senha") or ""
        confirmar_senha = request.form.get("confirmar_senha") or ""

        sucesso, mensagem, cliente = ClienteAuthService.cadastrar(
            nome=nome,
            telefone=telefone,
            email=email,
            cpf=cpf,
            senha=senha,
            confirmar_senha=confirmar_senha,
        )

        if not sucesso:
            flash(mensagem, "danger")
            return render_template(
                "cliente/cadastro.html",
                form_data={
                    "nome": nome,
                    "telefone": telefone,
                    "email": email,
                    "cpf": cpf,
                },
            )

        session["cliente"] = {
            "id": cliente["id"],
            "nome": cliente["nome"],
            "email": cliente["email"],
            "cpf": cliente.get("cpf", ""),
            "telefone": cliente.get("telefone", ""),
            "perfil": "CLIENTE",
        }

        flash("Cadastro realizado com sucesso.", "success")
        return redirect(url_for("cliente_auth.home"))

    return render_template("cliente/cadastro.html", form_data={})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("cliente"):
        return redirect(url_for("cliente_auth.home"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        senha = request.form.get("senha") or ""

        sucesso, mensagem, cliente = ClienteAuthService.autenticar(
            email=email,
            senha=senha,
        )

        if not sucesso:
            flash(mensagem, "danger")
            return render_template(
                "cliente/login.html",
                form_data={"email": email},
            )

        session["cliente"] = {
            "id": cliente["id"],
            "nome": cliente["nome"],
            "email": cliente["email"],
            "cpf": cliente.get("cpf", ""),
            "telefone": cliente.get("telefone", ""),
            "perfil": "CLIENTE",
        }

        flash("Login realizado com sucesso.", "success")
        return redirect(url_for("cliente_auth.home"))

    return render_template("cliente/login.html", form_data={})


@bp.get("/home")
@login_cliente_obrigatorio
def home():
    cliente_sessao = session.get("cliente") or {}
    cliente = ClienteAuthService.buscar_por_id(cliente_sessao.get("id"))

    if not cliente:
        session.pop("cliente", None)
        flash("Sessão inválida. Faça login novamente.", "warning")
        return redirect(url_for("cliente_auth.login"))

    if not cliente.get("ativo", True):
        session.pop("cliente", None)
        flash("Seu cadastro está inativo. Entre em contato com o suporte.", "warning")
        return redirect(url_for("cliente_auth.login"))

    ultimo_pedido = ClientePedidoService.buscar_ultimo_pedido_do_cliente(cliente.get("id"))

    return render_template(
        "cliente/home.html",
        cliente=cliente,
        ultimo_pedido=ultimo_pedido,
    )


@bp.get("/logout")
def logout():
    session.pop("cliente", None)
    flash("Logout realizado com sucesso.", "success")
    return redirect(url_for("cliente_auth.login"))