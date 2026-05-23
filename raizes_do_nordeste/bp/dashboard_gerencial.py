from flask import Blueprint, render_template, request

from services.dashboard_gerencial_service import DashboardGerencialService


bp = Blueprint(
    "dashboard_gerencial",
    __name__,
    url_prefix="/relatorios/dashboard-gerencial"
)


def moeda(valor):
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"


def _obter_filtros():
    return {
        "data_inicio": request.args.get("data_inicio", "").strip(),
        "data_fim": request.args.get("data_fim", "").strip(),
        "unidade_id": request.args.get("unidade_id", "").strip(),
        "origem": request.args.get("origem", "").strip(),
    }


@bp.app_template_filter("moeda")
def filtro_moeda(valor):
    return moeda(valor)


@bp.route("/", methods=["GET"])
def index():
    filtros = _obter_filtros()

    unidades = DashboardGerencialService.listar_unidades()

    resultado = DashboardGerencialService.gerar_dashboard(
        data_inicio=filtros["data_inicio"],
        data_fim=filtros["data_fim"],
        unidade_id=filtros["unidade_id"],
        origem=filtros["origem"],
    )

    return render_template(
        "relatorios/dashboard_gerencial.html",
        filtros=filtros,
        unidades=unidades,
        totais=resultado["totais"],
        operacional=resultado["operacional"],
        pedidos_operacionais=resultado["pedidos_operacionais"],
        resumo_por_filial=resultado["resumo_por_filial"],
        resumo_por_forma=resultado["resumo_por_forma"],
        resumo_por_status=resultado["resumo_por_status"],
        resumo_por_pagamento=resultado["resumo_por_pagamento"],
        resumo_por_origem=resultado["resumo_por_origem"],
        produtos_mais_vendidos=resultado["produtos_mais_vendidos"],
        ultimos_pedidos=resultado["ultimos_pedidos"],
    )