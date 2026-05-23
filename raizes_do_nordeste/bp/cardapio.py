from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils.decorators import login_required, perfil_required
from services.cardapio_service import CardapioService
from services.unidade_service import UnidadeService
from services.produto_service import ProdutoService

bp = Blueprint("cardapio", __name__, url_prefix="/cardapio")


@bp.route("/")
@login_required
@perfil_required("ADMIN", "GERENTE")
def lista():
    cardapios = CardapioService.listar()

    filtro_unidade = request.args.get("unidade", "").strip().lower()
    filtro_produto = request.args.get("produto", "").strip().lower()
    filtro_disponivel = request.args.get("disponivel", "").strip().upper()
    filtro_destaque = request.args.get("destaque", "").strip().upper()
    filtro_status = request.args.get("status", "").strip().upper()

    if filtro_unidade:
        cardapios = [
            c for c in cardapios
            if filtro_unidade in (c.get("nome_unidade", "") or "").lower()
        ]

    if filtro_produto:
        cardapios = [
            c for c in cardapios
            if filtro_produto in (c.get("nome_produto", "") or "").lower()
        ]

    if filtro_disponivel:
        disponivel_filtro = filtro_disponivel == "SIM"
        cardapios = [
            c for c in cardapios
            if bool(c.get("disponivel", False)) == disponivel_filtro
        ]

    if filtro_destaque:
        destaque_filtro = filtro_destaque == "SIM"
        cardapios = [
            c for c in cardapios
            if bool(c.get("destaque", False)) == destaque_filtro
        ]

    if filtro_status:
        ativo_filtro = filtro_status == "ATIVO"
        cardapios = [
            c for c in cardapios
            if bool(c.get("ativo", False)) == ativo_filtro
        ]

    filtros = {
        "unidade": request.args.get("unidade", "").strip(),
        "produto": request.args.get("produto", "").strip(),
        "disponivel": request.args.get("disponivel", "").strip(),
        "destaque": request.args.get("destaque", "").strip(),
        "status": request.args.get("status", "").strip(),
    }

    return render_template("cardapio/lista.html", cardapios=cardapios, filtros=filtros)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def novo():
    unidades = UnidadeService.listar()
    produtos = ProdutoService.listar()

    if request.method == "POST":
        try:
            unidade_id = request.form.get("unidade_id", "").strip()
            produto_id = request.form.get("produto_id", "").strip()
            preco_venda = request.form.get("preco_venda", "").strip()

            if not unidade_id:
                flash("A unidade é obrigatória.", "warning")
                return render_template(
                    "cardapio/form.html",
                    cardapio=request.form,
                    unidades=unidades,
                    produtos=produtos,
                )

            if not produto_id:
                flash("O produto é obrigatório.", "warning")
                return render_template(
                    "cardapio/form.html",
                    cardapio=request.form,
                    unidades=unidades,
                    produtos=produtos,
                )

            if not preco_venda:
                flash("O preço de venda é obrigatório.", "warning")
                return render_template(
                    "cardapio/form.html",
                    cardapio=request.form,
                    unidades=unidades,
                    produtos=produtos,
                )

            CardapioService.criar(request.form)
            flash("Item do cardápio cadastrado com sucesso.", "success")
            return redirect(url_for("cardapio.lista"))

        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Erro ao cadastrar item do cardápio.", "danger")

    return render_template(
        "cardapio/form.html",
        cardapio=None,
        unidades=unidades,
        produtos=produtos,
    )


@bp.route("/editar/<cardapio_id>", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN", "GERENTE")
def editar(cardapio_id):
    cardapio = CardapioService.buscar_por_id(cardapio_id)

    if not cardapio:
        flash("Item do cardápio não encontrado.", "danger")
        return redirect(url_for("cardapio.lista"))

    unidades = UnidadeService.listar()
    produtos = ProdutoService.listar()

    if request.method == "POST":
        try:
            unidade_id = request.form.get("unidade_id", "").strip()
            produto_id = request.form.get("produto_id", "").strip()
            preco_venda = request.form.get("preco_venda", "").strip()

            if not unidade_id:
                flash("A unidade é obrigatória.", "warning")
                return render_template(
                    "cardapio/form.html",
                    cardapio=request.form,
                    unidades=unidades,
                    produtos=produtos,
                )

            if not produto_id:
                flash("O produto é obrigatório.", "warning")
                return render_template(
                    "cardapio/form.html",
                    cardapio=request.form,
                    unidades=unidades,
                    produtos=produtos,
                )

            if not preco_venda:
                flash("O preço de venda é obrigatório.", "warning")
                return render_template(
                    "cardapio/form.html",
                    cardapio=request.form,
                    unidades=unidades,
                    produtos=produtos,
                )

            CardapioService.atualizar(cardapio_id, request.form)
            flash("Item do cardápio atualizado com sucesso.", "success")
            return redirect(url_for("cardapio.lista"))

        except ValueError as e:
            flash(str(e), "warning")
        except Exception:
            flash("Erro ao atualizar item do cardápio.", "danger")

    return render_template(
        "cardapio/form.html",
        cardapio=cardapio,
        unidades=unidades,
        produtos=produtos,
    )


@bp.route("/status/<cardapio_id>/<acao>")
@login_required
@perfil_required("ADMIN", "GERENTE")
def alterar_status(cardapio_id, acao):
    ativo = acao == "ativar"
    CardapioService.alterar_status(cardapio_id, ativo)
    flash("Status do item do cardápio alterado com sucesso.", "success")
    return redirect(url_for("cardapio.lista"))