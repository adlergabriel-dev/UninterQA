from flask import Blueprint, render_template, session

from utils.decorators import login_required
from services.unidade_service import UnidadeService
from services.produto_service import ProdutoService
from services.cliente_service import ClienteService
from services.cardapio_service import CardapioService
from services.pedido_service import PedidoService

bp = Blueprint("home", __name__)


@bp.route("/")
@login_required
def index():
    usuario = session.get("usuario", {})

    unidades = UnidadeService.listar()
    produtos = ProdutoService.listar()
    clientes = ClienteService.listar()
    cardapios = CardapioService.listar()
    pedidos = PedidoService.listar()

    total_unidades = len(unidades)
    total_unidades_ativas = len([u for u in unidades if u.get("ativo", False)])

    total_produtos = len(produtos)
    total_produtos_ativos = len([p for p in produtos if p.get("ativo", False)])

    total_clientes = len(clientes)
    total_clientes_ativos = len([c for c in clientes if c.get("ativo", False)])

    total_cardapio = len(cardapios)
    total_cardapio_ativos = len([c for c in cardapios if c.get("ativo", False)])
    total_cardapio_disponiveis = len([
        c for c in cardapios
        if c.get("ativo", False) and c.get("disponivel", False)
    ])

    total_pedidos = len(pedidos)
    pedidos_aguardando_pagamento = len([p for p in pedidos if p.get("status") == "AGUARDANDO_PAGAMENTO"])
    pedidos_pagos = len([p for p in pedidos if p.get("status") == "PAGO"])
    pedidos_em_preparo = len([p for p in pedidos if p.get("status") == "EM_PREPARO"])
    pedidos_prontos = len([p for p in pedidos if p.get("status") == "PRONTO_PARA_RETIRADA"])
    pedidos_saida_entrega = len([p for p in pedidos if p.get("status") == "SAIU_PARA_ENTREGA"])
    pedidos_concluidos = len([p for p in pedidos if p.get("status") == "CONCLUIDO"])
    pedidos_cancelados = len([p for p in pedidos if p.get("status") == "CANCELADO"])

    ultimos_pedidos = pedidos[:5]

    resumo = {
        "total_unidades": total_unidades,
        "total_unidades_ativas": total_unidades_ativas,
        "total_produtos": total_produtos,
        "total_produtos_ativos": total_produtos_ativos,
        "total_clientes": total_clientes,
        "total_clientes_ativos": total_clientes_ativos,
        "total_cardapio": total_cardapio,
        "total_cardapio_ativos": total_cardapio_ativos,
        "total_cardapio_disponiveis": total_cardapio_disponiveis,
        "total_pedidos": total_pedidos,
        "pedidos_aguardando_pagamento": pedidos_aguardando_pagamento,
        "pedidos_pagos": pedidos_pagos,
        "pedidos_em_preparo": pedidos_em_preparo,
        "pedidos_prontos": pedidos_prontos,
        "pedidos_saida_entrega": pedidos_saida_entrega,
        "pedidos_concluidos": pedidos_concluidos,
        "pedidos_cancelados": pedidos_cancelados,
    }

    return render_template(
        "home/index.html",
        usuario=usuario,
        resumo=resumo,
        ultimos_pedidos=ultimos_pedidos,
    )