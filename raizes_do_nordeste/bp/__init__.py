from bp.auth import bp as auth_bp
from bp.home import bp as home_bp
from bp.usuarios import bp as usuarios_bp
from bp.unidades import bp as unidades_bp
from bp.produtos import bp as produtos_bp
from bp.clientes import bp as clientes_bp
from bp.cardapio import bp as cardapio_bp
from bp.pedidos import bp as pedidos_bp
from bp.auditoria import bp as auditoria_bp

from bp.cliente_auth import bp as cliente_auth_bp
from bp.cliente_portal import bp as cliente_portal_bp
from bp.cliente_cardapio import bp as cliente_cardapio_bp
from bp.cliente_pedido import bp as cliente_pedido_bp

from bp.pedidos_admin import bp as pedidos_admin_bp
from bp.pedido_balcao import bp as pedido_balcao_bp
from bp.pedido_totem import bp as pedido_totem_bp
from bp.cozinha import bp as cozinha_bp
from bp.retirada import bp as retirada_bp

from bp.relatorios import bp as relatorios_bp
from bp.relatorio_pedido_balcao import bp as relatorio_pedido_balcao_bp
from bp.fechamento_caixa import bp as fechamento_caixa_bp
from bp.relatorio_produtos_vendidos import bp as relatorio_produtos_vendidos_bp
from bp.dashboard_gerencial import bp as dashboard_gerencial_bp
from bp.relatorio_clientes_compraram import bp as relatorio_clientes_compraram_bp
from bp.relatorio_movimento_diario import bp as relatorio_movimento_diario_bp


def register_blueprints(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(unidades_bp)
    app.register_blueprint(produtos_bp)
    app.register_blueprint(clientes_bp)
    app.register_blueprint(cardapio_bp)
    app.register_blueprint(pedidos_bp)
    app.register_blueprint(auditoria_bp)

    app.register_blueprint(cliente_auth_bp)
    app.register_blueprint(cliente_portal_bp)
    app.register_blueprint(cliente_cardapio_bp)
    app.register_blueprint(cliente_pedido_bp)

    app.register_blueprint(pedidos_admin_bp)
    app.register_blueprint(pedido_balcao_bp)
    app.register_blueprint(pedido_totem_bp)
    app.register_blueprint(cozinha_bp)
    app.register_blueprint(retirada_bp)

    app.register_blueprint(relatorios_bp)
    app.register_blueprint(relatorio_pedido_balcao_bp)
    app.register_blueprint(fechamento_caixa_bp)
    app.register_blueprint(relatorio_produtos_vendidos_bp)
    app.register_blueprint(dashboard_gerencial_bp)
    app.register_blueprint(relatorio_clientes_compraram_bp)
    app.register_blueprint(relatorio_movimento_diario_bp)