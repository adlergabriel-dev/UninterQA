from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils.decorators import login_required, perfil_required
from services.produto_service import ProdutoService

bp = Blueprint("produtos", __name__, url_prefix="/produtos")


@bp.route("/")
@login_required
@perfil_required("ADMIN", "GERENTE")
def lista():
    produtos = ProdutoService.listar()

    filtro_nome = request.args.get("nome", "").strip().lower()
    filtro_categoria = request.args.get("categoria", "").strip().lower()
    filtro_sku = request.args.get("sku", "").strip().upper()
    filtro_status = request.args.get("status", "").strip().upper()

    if filtro_nome:
        produtos = [
            p for p in produtos
            if filtro_nome in (p.get("nome", "") or "").lower()
        ]

    if filtro_categoria:
        produtos = [
            p for p in produtos
            if filtro_categoria in (p.get("categoria", "") or "").lower()
        ]

    if filtro_sku:
        produtos = [
            p for p in produtos
            if filtro_sku in (p.get("sku", "") or "").upper()
        ]

    if filtro_status:
        ativo_filtro = filtro_status == "ATIVO"
        produtos = [
            p for p in produtos
            if bool(p.get("ativo", False)) == ativo_filtro
        ]

    filtros = {
        "nome": request.args.get("nome", "").strip(),
        "categoria": request.args.get("categoria", "").strip(),
        "sku": request.args.get("sku", "").strip(),
        "status": request.args.get("status", "").strip(),
    }

    return render_template("produtos/lista.html", produtos=produtos, filtros=filtros)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def novo():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        categoria = request.form.get("categoria", "").strip()

        if not nome:
            flash("O nome do produto é obrigatório.", "warning")
            return render_template("produtos/form.html", produto=request.form)

        if not categoria:
            flash("A categoria do produto é obrigatória.", "warning")
            return render_template("produtos/form.html", produto=request.form)

        ProdutoService.criar(request.form)
        flash("Produto cadastrado com sucesso.", "success")
        return redirect(url_for("produtos.lista"))

    return render_template("produtos/form.html", produto=None)


@bp.route("/editar/<produto_id>", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def editar(produto_id):
    produto = ProdutoService.buscar_por_id(produto_id)

    if not produto:
        flash("Produto não encontrado.", "danger")
        return redirect(url_for("produtos.lista"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        categoria = request.form.get("categoria", "").strip()

        if not nome:
            flash("O nome do produto é obrigatório.", "warning")
            return render_template("produtos/form.html", produto=request.form)

        if not categoria:
            flash("A categoria do produto é obrigatória.", "warning")
            return render_template("produtos/form.html", produto=request.form)

        ProdutoService.atualizar(produto_id, request.form)
        flash("Produto atualizado com sucesso.", "success")
        return redirect(url_for("produtos.lista"))

    return render_template("produtos/form.html", produto=produto)


@bp.route("/status/<produto_id>/<acao>")
@login_required
@perfil_required("ADMIN", "GERENTE")
def alterar_status(produto_id, acao):
    ativo = acao == "ativar"
    ProdutoService.alterar_status(produto_id, ativo)
    flash("Status do produto alterado com sucesso.", "success")
    return redirect(url_for("produtos.lista"))