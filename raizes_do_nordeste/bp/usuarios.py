from flask import Blueprint, render_template, request, redirect, url_for, flash

from utils.decorators import login_required, perfil_required
from services.usuario_service import UsuarioService

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@bp.route("/")
@login_required
@perfil_required("ADMIN")
def lista():
    usuarios = UsuarioService.listar()
    return render_template("usuarios/lista.html", usuarios=usuarios)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN")
def novo():
    if request.method == "POST":
        try:
            UsuarioService.criar(request.form)
            flash("Usuário cadastrado com sucesso.", "success")
            return redirect(url_for("usuarios.lista"))
        except ValueError as e:
            flash(str(e), "warning")
        except Exception as e:
            flash(f"Erro ao cadastrar usuário: {str(e)}", "danger")

        return render_template(
            "usuarios/form.html",
            usuario_form=dict(request.form),
            editando=False
        )

    return render_template(
        "usuarios/form.html",
        usuario_form=None,
        editando=False
    )


@bp.route("/editar/<usuario_id>", methods=["GET", "POST"])
@login_required
@perfil_required("ADMIN")
def editar(usuario_id):
    print(f"[DEBUG USUARIOS] Editando documento Firestore: {usuario_id}")

    usuario_form = UsuarioService.buscar_por_id(usuario_id)

    if not usuario_form:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("usuarios.lista"))

    usuario_form["id"] = usuario_id
    usuario_form["doc_id"] = usuario_id

    print(
        "[DEBUG USUARIOS] Usuário carregado:",
        usuario_form.get("nome"),
        usuario_form.get("email"),
        usuario_form.get("uid"),
    )

    if request.method == "POST":
        try:
            UsuarioService.atualizar(usuario_id, request.form)
            flash("Usuário atualizado com sucesso.", "success")
            return redirect(url_for("usuarios.lista"))
        except ValueError as e:
            flash(str(e), "warning")
        except Exception as e:
            flash(f"Erro ao atualizar usuário: {str(e)}", "danger")

        dados_form = dict(request.form)
        dados_form["id"] = usuario_id
        dados_form["doc_id"] = usuario_id
        dados_form["uid"] = usuario_form.get("uid", "")

        return render_template(
            "usuarios/form.html",
            usuario_form=dados_form,
            editando=True
        )

    return render_template(
        "usuarios/form.html",
        usuario_form=usuario_form,
        editando=True
    )


@bp.route("/status/<usuario_id>/<acao>")
@login_required
@perfil_required("ADMIN")
def alterar_status(usuario_id, acao):
    try:
        if acao not in ["ativar", "inativar"]:
            flash("Ação inválida.", "warning")
            return redirect(url_for("usuarios.lista"))

        ativo = acao == "ativar"
        UsuarioService.alterar_status(usuario_id, ativo)
        flash("Status do usuário alterado com sucesso.", "success")
    except ValueError as e:
        flash(str(e), "warning")
    except Exception as e:
        flash(f"Erro ao alterar status do usuário: {str(e)}", "danger")

    return redirect(url_for("usuarios.lista"))