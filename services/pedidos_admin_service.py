from datetime import datetime

from services.firebase_service import FirebaseService
from services.auditoria_service import AuditoriaService


class PedidosAdminService:
    COLLECTION_PEDIDOS = "pedidos"
    COLLECTION_UNIDADES = "unidades"
    COLLECTION_FECHAMENTOS = "fechamentos_caixa"

    STATUS_ABERTO = "ABERTO"
    STATUS_CRIADO = "CRIADO"
    STATUS_EM_PREPARO = "EM_PREPARO"
    STATUS_PRONTO = "PRONTO"
    STATUS_ENVIADO = "ENVIADO"
    STATUS_ENTREGUE = "ENTREGUE"
    STATUS_FINALIZADO = "FINALIZADO"
    STATUS_CANCELADO = "CANCELADO"

    PAGAMENTO_AGUARDANDO = "AGUARDANDO_PAGAMENTO"
    PAGAMENTO_PENDENTE = "PENDENTE"
    PAGAMENTO_PAGO = "PAGO"
    PAGAMENTO_RECUSADO = "RECUSADO"

    ORIGENS = ["CLIENTE_WEB", "BALCAO"]

    TRANSICOES = {
        STATUS_ABERTO: [STATUS_EM_PREPARO, STATUS_CANCELADO],
        STATUS_CRIADO: [STATUS_EM_PREPARO, STATUS_CANCELADO],
        STATUS_EM_PREPARO: [STATUS_PRONTO, STATUS_ENVIADO, STATUS_CANCELADO],
        STATUS_PRONTO: [STATUS_ENTREGUE, STATUS_FINALIZADO],
        STATUS_ENVIADO: [STATUS_ENTREGUE, STATUS_FINALIZADO],
        STATUS_ENTREGUE: [],
        STATUS_FINALIZADO: [],
        STATUS_CANCELADO: [],
    }

    @classmethod
    def _collection(cls, nome):
        return FirebaseService.get_collection(nome)

    @classmethod
    def _texto(cls, valor):
        return str(valor or "").strip()

    @classmethod
    def _texto_lower(cls, valor):
        return cls._texto(valor).lower()

    @classmethod
    def _bool(cls, valor, default=True):
        if isinstance(valor, bool):
            return valor

        if valor is None:
            return default

        if isinstance(valor, str):
            return valor.strip().lower() in ["true", "1", "sim", "yes", "ativo"]

        return bool(valor)

    @classmethod
    def _agora_iso(cls):
        return datetime.utcnow().isoformat()

    @classmethod
    def _formatar_moeda(cls, valor):
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @classmethod
    def _normalizar_origem(cls, data):
        origem = cls._texto(
            data.get("origem")
            or data.get("tipo")
            or data.get("canal")
        ).upper()

        if origem == "PEDIDO_BALCAO":
            return "BALCAO"

        if origem == "WEB":
            return "CLIENTE_WEB"

        if origem:
            return origem

        return "-"

    @classmethod
    def _normalizar_status(cls, status):
        status = cls._texto(status).upper()

        if status == cls.STATUS_CRIADO:
            return cls.STATUS_ABERTO

        if status == cls.STATUS_FINALIZADO:
            return cls.STATUS_ENTREGUE

        validos = {
            cls.STATUS_ABERTO,
            cls.STATUS_EM_PREPARO,
            cls.STATUS_PRONTO,
            cls.STATUS_ENVIADO,
            cls.STATUS_ENTREGUE,
            cls.STATUS_CANCELADO,
        }

        return status if status in validos else cls.STATUS_ABERTO

    @classmethod
    def _descricao_status(cls, status):
        mapa = {
            cls.STATUS_ABERTO: "Aberto",
            cls.STATUS_EM_PREPARO: "Em preparo",
            cls.STATUS_PRONTO: "Pronto",
            cls.STATUS_ENVIADO: "Enviado",
            cls.STATUS_ENTREGUE: "Entregue",
            cls.STATUS_CANCELADO: "Cancelado",
        }

        return mapa.get(cls._normalizar_status(status), "Aberto")

    @classmethod
    def _classe_status(cls, status):
        status = cls._normalizar_status(status)

        mapa = {
            cls.STATUS_ABERTO: "status-badge status-aberto",
            cls.STATUS_EM_PREPARO: "status-badge status-preparo",
            cls.STATUS_PRONTO: "status-badge status-enviado",
            cls.STATUS_ENVIADO: "status-badge status-enviado",
            cls.STATUS_ENTREGUE: "status-badge status-entregue",
            cls.STATUS_CANCELADO: "status-badge status-cancelado",
        }

        return mapa.get(status, "status-badge")

    @classmethod
    def _normalizar_pagamento_status(cls, data):
        status = cls._texto(
            data.get("pagamento_status")
            or data.get("situacao_pagamento")
            or data.get("status_pagamento")
        ).upper()

        if status == cls.PAGAMENTO_PENDENTE:
            return cls.PAGAMENTO_AGUARDANDO

        if status in {
            cls.PAGAMENTO_AGUARDANDO,
            cls.PAGAMENTO_PAGO,
            cls.PAGAMENTO_RECUSADO,
        }:
            return status

        return cls.PAGAMENTO_AGUARDANDO

    @classmethod
    def _descricao_pagamento(cls, status):
        status = cls._texto(status).upper()

        mapa = {
            cls.PAGAMENTO_AGUARDANDO: "Aguardando pagamento",
            cls.PAGAMENTO_PENDENTE: "Pendente",
            cls.PAGAMENTO_PAGO: "Pago",
            cls.PAGAMENTO_RECUSADO: "Recusado",
        }

        return mapa.get(status, "Aguardando pagamento")

    @classmethod
    def _classe_pagamento(cls, status):
        status = cls._texto(status).upper()

        mapa = {
            cls.PAGAMENTO_AGUARDANDO: "status-badge status-aberto",
            cls.PAGAMENTO_PENDENTE: "status-badge status-aberto",
            cls.PAGAMENTO_PAGO: "status-badge status-entregue",
            cls.PAGAMENTO_RECUSADO: "status-badge status-cancelado",
        }

        return mapa.get(status, "status-badge")

    @classmethod
    def buscar_fechamento_do_pedido(cls, pedido_id):
        pedido_id = cls._texto(pedido_id)

        if not pedido_id:
            return None

        docs = cls._collection(cls.COLLECTION_FECHAMENTOS).stream()

        for doc in docs:
            item = doc.to_dict() or {}
            pedidos_ids = item.get("pedidos_ids") or []

            if not isinstance(pedidos_ids, list):
                continue

            if pedido_id in pedidos_ids:
                item["id"] = doc.id
                return item

        return None

    @classmethod
    def pedido_esta_em_fechamento(cls, pedido_id):
        return cls.buscar_fechamento_do_pedido(pedido_id) is not None

    @classmethod
    def _pagamento_pago(cls, pedido):
        return (pedido.get("pagamento_status") or "").upper() == cls.PAGAMENTO_PAGO

    @classmethod
    def _pedido_finalizado_ou_cancelado(cls, pedido):
        return pedido.get("status") in [
            cls.STATUS_ENTREGUE,
            cls.STATUS_FINALIZADO,
            cls.STATUS_CANCELADO,
        ]

    @classmethod
    def _montar_acoes_rapidas(cls, pedido):
        status = pedido.get("status")
        pagamento_status = (pedido.get("pagamento_status") or "").upper()
        fechado_em_caixa = bool(pedido.get("fechado_em_caixa"))

        if fechado_em_caixa:
            return {
                "pode_confirmar_pagamento": False,
                "pode_enviar_preparo": False,
                "pode_marcar_pronto": False,
                "pode_finalizar": False,
                "pode_cancelar": False,
            }

        finalizado_ou_cancelado = status in [
            cls.STATUS_ENTREGUE,
            cls.STATUS_FINALIZADO,
            cls.STATUS_CANCELADO,
        ]

        return {
            "pode_confirmar_pagamento": (
                pagamento_status != cls.PAGAMENTO_PAGO
                and status != cls.STATUS_CANCELADO
            ),
            "pode_enviar_preparo": (
                pagamento_status == cls.PAGAMENTO_PAGO
                and status == cls.STATUS_ABERTO
            ),
            "pode_marcar_pronto": (
                pagamento_status == cls.PAGAMENTO_PAGO
                and status == cls.STATUS_EM_PREPARO
            ),
            "pode_finalizar": (
                pagamento_status == cls.PAGAMENTO_PAGO
                and status in [cls.STATUS_PRONTO, cls.STATUS_ENVIADO]
            ),
            "pode_cancelar": not finalizado_ou_cancelado,
        }

    @classmethod
    def _to_float(cls, valor):
        try:
            return float(valor or 0)
        except Exception:
            return 0.0

    @classmethod
    def _to_int(cls, valor):
        try:
            return int(float(valor or 0))
        except Exception:
            return 0

    @classmethod
    def _normalizar_item(cls, item):
        item = item or {}
        snapshot = item.get("snapshot_produto") or {}

        nome = cls._texto(
            item.get("produto_nome")
            or item.get("nome_produto")
            or item.get("nome")
            or snapshot.get("produto_nome")
            or snapshot.get("nome")
        )

        descricao = cls._texto(
            item.get("produto_descricao")
            or item.get("descricao_produto")
            or item.get("descricao")
            or snapshot.get("produto_descricao")
            or snapshot.get("descricao")
        )

        quantidade = cls._to_int(
            item.get("quantidade")
            or item.get("qtd")
            or item.get("qtde")
        )

        valor_unitario = cls._to_float(
            item.get("valor_unitario")
            or item.get("preco_unitario")
            or item.get("preco")
            or item.get("valor")
            or snapshot.get("preco_unitario")
            or snapshot.get("preco")
        )

        subtotal = cls._to_float(
            item.get("valor_total")
            or item.get("subtotal")
            or item.get("valor_subtotal")
            or item.get("total")
        )

        if subtotal <= 0 and quantidade > 0:
            subtotal = quantidade * valor_unitario

        snapshot_normalizado = {
            "nome": nome or "-",
            "produto_nome": nome or "-",
            "descricao": descricao or "-",
            "produto_descricao": descricao or "-",
            "preco": valor_unitario,
            "preco_unitario": valor_unitario,
            "preco_formatado": cls._formatar_moeda(valor_unitario),
        }

        return {
            "cardapio_id": cls._texto(item.get("cardapio_id")),
            "produto_id": cls._texto(item.get("produto_id")),
            "produto_nome": nome or "-",
            "nome": nome or "-",
            "descricao": descricao or "-",
            "produto_descricao": descricao or "-",
            "quantidade": quantidade,
            "valor_unitario": valor_unitario,
            "preco_unitario": valor_unitario,
            "valor_unitario_formatado": cls._formatar_moeda(valor_unitario),
            "preco_unitario_formatado": cls._formatar_moeda(valor_unitario),
            "subtotal": subtotal,
            "valor_total": subtotal,
            "subtotal_formatado": cls._formatar_moeda(subtotal),
            "observacao": cls._texto(item.get("observacao")),
            "snapshot_produto": snapshot_normalizado,
        }

    @classmethod
    def _normalizar_itens(cls, itens):
        itens = itens or []

        if not isinstance(itens, list):
            return []

        return [cls._normalizar_item(item) for item in itens if isinstance(item, dict)]

    @classmethod
    def _novo_evento_historico(
        cls,
        tipo,
        descricao,
        usuario_tipo,
        usuario_nome,
        status_anterior="",
        status_novo="",
        motivo="",
    ):
        return {
            "tipo": cls._texto(tipo).upper(),
            "descricao": cls._texto(descricao),
            "usuario_tipo": cls._texto(usuario_tipo).upper(),
            "usuario_nome": cls._texto(usuario_nome),
            "status_anterior": cls._texto(status_anterior).upper(),
            "status_novo": cls._texto(status_novo).upper(),
            "motivo": cls._texto(motivo),
            "criado_em": cls._agora_iso(),
        }

    @classmethod
    def listar_status(cls):
        return [
            cls.STATUS_ABERTO,
            cls.STATUS_EM_PREPARO,
            cls.STATUS_PRONTO,
            cls.STATUS_ENVIADO,
            cls.STATUS_ENTREGUE,
            cls.STATUS_CANCELADO,
        ]

    @classmethod
    def listar_origens(cls):
        return cls.ORIGENS

    @classmethod
    def listar_unidades_ativas(cls):
        docs = cls._collection(cls.COLLECTION_UNIDADES).stream()
        unidades = []

        for doc in docs:
            data = doc.to_dict() or {}

            if not cls._bool(data.get("ativo"), True):
                continue

            unidades.append({
                "id": doc.id,
                "nome": cls._texto(data.get("nome")),
            })

        unidades.sort(key=lambda x: cls._texto_lower(x.get("nome")))
        return unidades

    @classmethod
    def _normalizar_pedido(cls, doc_id, data):
        data = data or {}

        status = cls._normalizar_status(data.get("status"))

        valor_total = cls._to_float(
            data.get("valor_total")
            or data.get("total")
            or data.get("pagamento_valor")
        )

        historico = data.get("historico") or []
        historico.sort(key=lambda x: cls._texto(x.get("criado_em")), reverse=True)

        pagamento_status = cls._normalizar_pagamento_status(data)
        pagamento_valor = cls._to_float(data.get("pagamento_valor") or valor_total)

        itens = cls._normalizar_itens(data.get("itens") or [])

        quantidade_total_itens = cls._to_int(
            data.get("quantidade_total_itens")
            or data.get("qtd_total_itens")
        )

        if quantidade_total_itens <= 0:
            quantidade_total_itens = sum(item.get("quantidade", 0) for item in itens)

        quantidade_itens = cls._to_int(data.get("quantidade_itens"))

        if quantidade_itens <= 0:
            quantidade_itens = quantidade_total_itens

        fechamento = cls.buscar_fechamento_do_pedido(doc_id)
        fechado_em_caixa = fechamento is not None

        pedido_normalizado = {
            "id": doc_id,
            "codigo_pedido": cls._texto(data.get("codigo_pedido")),
            "cliente_id": cls._texto(data.get("cliente_id")),
            "cliente_nome": cls._texto(data.get("cliente_nome")),
            "cliente_email": cls._texto(data.get("cliente_email")),
            "cliente_telefone": cls._texto(data.get("cliente_telefone")),
            "unidade_id": cls._texto(data.get("unidade_id")),
            "unidade_nome": cls._texto(data.get("unidade_nome")),

            "status": status,
            "status_descricao": cls._descricao_status(status),
            "status_classe": cls._classe_status(status),

            "origem": cls._normalizar_origem(data),

            "pagamento_status": pagamento_status,
            "pagamento_status_descricao": (
                cls._texto(data.get("pagamento_status_descricao"))
                or cls._descricao_pagamento(pagamento_status)
            ),
            "pagamento_status_classe": cls._classe_pagamento(pagamento_status),

            "pagamento_metodo": cls._texto(
                data.get("pagamento_metodo")
                or data.get("forma_pagamento")
            ),
            "pagamento_metodo_descricao": cls._texto(
                data.get("pagamento_metodo_descricao")
                or data.get("pagamento_metodo")
                or data.get("forma_pagamento")
            ),

            "pagamento_valor": pagamento_valor,
            "pagamento_valor_formatado": (
                cls._texto(data.get("pagamento_valor_formatado"))
                or cls._formatar_moeda(pagamento_valor)
            ),
            "pagamento_transacao_id": cls._texto(data.get("pagamento_transacao_id")),
            "pago_em": cls._texto(data.get("pago_em")),

            "itens": itens,
            "historico": historico,

            "quantidade_itens": quantidade_itens,
            "quantidade_total_itens": quantidade_total_itens,

            "valor_total": valor_total,
            "valor_total_formatado": (
                cls._texto(data.get("valor_total_formatado"))
                or cls._formatar_moeda(valor_total)
            ),

            "criado_em": cls._texto(data.get("criado_em")),
            "criado_em_ord": cls._texto(data.get("criado_em_ord")),
            "atualizado_em": cls._texto(data.get("atualizado_em")),
            "cancelado_em": cls._texto(data.get("cancelado_em")),
            "motivo_cancelamento": cls._texto(data.get("motivo_cancelamento")),

            "status_atualizado_por": cls._texto(
                data.get("status_atualizado_por")
                or data.get("status_atualizado_por_nome")
            ),

            "fechado_em_caixa": fechado_em_caixa,
            "fechamento_caixa": {
                "id": fechamento.get("id", "") if fechamento else "",
                "data_inicio": fechamento.get("data_inicio", "") if fechamento else "",
                "data_fim": fechamento.get("data_fim", "") if fechamento else "",
                "unidade_nome": fechamento.get("unidade_nome", "") if fechamento else "",
                "criado_em_texto": fechamento.get("criado_em_texto", "") if fechamento else "",
                "usuario_nome": fechamento.get("usuario_nome", "") if fechamento else "",
            } if fechamento else {},
        }

        pedido_normalizado["acoes_rapidas"] = cls._montar_acoes_rapidas(pedido_normalizado)

        return pedido_normalizado

    @classmethod
    def listar_pedidos(cls, filtros=None):
        filtros = filtros or {}
        docs = cls._collection(cls.COLLECTION_PEDIDOS).stream()

        codigo_pedido = cls._texto_lower(filtros.get("codigo_pedido"))
        cliente_nome = cls._texto_lower(filtros.get("cliente_nome"))
        unidade_id = cls._texto(filtros.get("unidade_id"))
        status = cls._normalizar_status(filtros.get("status")) if filtros.get("status") else ""
        origem = cls._texto(filtros.get("origem")).upper()

        pedidos = []

        for doc in docs:
            pedido = cls._normalizar_pedido(doc.id, doc.to_dict())

            if codigo_pedido and codigo_pedido not in cls._texto_lower(pedido.get("codigo_pedido")):
                continue

            if cliente_nome and cliente_nome not in cls._texto_lower(pedido.get("cliente_nome")):
                continue

            if unidade_id and pedido.get("unidade_id") != unidade_id:
                continue

            if status and pedido.get("status") != status:
                continue

            if origem and pedido.get("origem") != origem:
                continue

            pedidos.append(pedido)

        pedidos.sort(
            key=lambda x: x.get("criado_em_ord") or x.get("criado_em", ""),
            reverse=True
        )

        return pedidos

    @classmethod
    def listar_pedidos_cozinha(cls, filtros=None):
        filtros = filtros or {}
        pedidos = cls.listar_pedidos(filtros=filtros)

        status_cozinha = {
            cls.STATUS_ABERTO,
            cls.STATUS_EM_PREPARO,
            cls.STATUS_PRONTO,
            cls.STATUS_ENVIADO,
        }

        pedidos_cozinha = []

        for pedido in pedidos:
            status = pedido.get("status")
            pagamento_status = (pedido.get("pagamento_status") or "").upper()

            if status not in status_cozinha:
                continue

            if pagamento_status != cls.PAGAMENTO_PAGO:
                continue

            pedidos_cozinha.append(pedido)

        return pedidos_cozinha

    @classmethod
    def listar_pedidos_retirada(cls, filtros=None):
        filtros = filtros or {}
        pedidos = cls.listar_pedidos(filtros=filtros)

        status_retirada = {
            cls.STATUS_PRONTO,
            cls.STATUS_ENVIADO,
        }

        pedidos_retirada = []

        for pedido in pedidos:
            status = pedido.get("status")
            pagamento_status = (pedido.get("pagamento_status") or "").upper()

            if status not in status_retirada:
                continue

            if pagamento_status != cls.PAGAMENTO_PAGO:
                continue

            pedidos_retirada.append(pedido)

        return pedidos_retirada

    @classmethod
    def montar_dashboard(cls, pedidos):
        pedidos = pedidos or []

        resumo = {
            "total_pedidos": len(pedidos),
            "abertos": 0,
            "em_preparo": 0,
            "prontos": 0,
            "enviados": 0,
            "entregues": 0,
            "cancelados": 0,
            "valor_total": 0.0,
            "valor_total_formatado": cls._formatar_moeda(0),
        }

        for pedido in pedidos:
            status = cls._normalizar_status(pedido.get("status"))
            valor = float(pedido.get("valor_total") or 0.0)

            resumo["valor_total"] += valor

            if status == cls.STATUS_ABERTO:
                resumo["abertos"] += 1

            elif status == cls.STATUS_EM_PREPARO:
                resumo["em_preparo"] += 1

            elif status == cls.STATUS_PRONTO:
                resumo["prontos"] += 1

            elif status == cls.STATUS_ENVIADO:
                resumo["enviados"] += 1

            elif status == cls.STATUS_ENTREGUE:
                resumo["entregues"] += 1

            elif status == cls.STATUS_CANCELADO:
                resumo["cancelados"] += 1

        resumo["valor_total_formatado"] = cls._formatar_moeda(resumo["valor_total"])
        return resumo

    @classmethod
    def buscar_pedido_por_id(cls, pedido_id):
        pedido_id = cls._texto(pedido_id)

        if not pedido_id:
            return None

        doc = cls._collection(cls.COLLECTION_PEDIDOS).document(pedido_id).get()

        if not doc.exists:
            return None

        return cls._normalizar_pedido(doc.id, doc.to_dict())

    @classmethod
    def listar_proximos_status(cls, status_atual):
        status_atual = cls._normalizar_status(status_atual)
        return cls.TRANSICOES.get(status_atual, [])

    @classmethod
    def alterar_status_pedido(cls, pedido_id, novo_status, usuario_nome):
        pedido = cls.buscar_pedido_por_id(pedido_id)

        if not pedido:
            return False, "Pedido não encontrado.", None

        if pedido.get("fechado_em_caixa"):
            fechamento = pedido.get("fechamento_caixa") or {}
            return (
                False,
                f"Pedido bloqueado. Ele já faz parte do fechamento de caixa {fechamento.get('id', '')}.",
                pedido,
            )

        status_anterior = pedido.get("status")
        novo_status = cls._normalizar_status(novo_status)
        proximos = cls.listar_proximos_status(status_anterior)

        if novo_status not in proximos:
            return False, "Transição de status inválida.", pedido

        if status_anterior == cls.STATUS_CANCELADO:
            return False, "Pedido cancelado não pode ter status alterado.", pedido

        agora = cls._agora_iso()
        historico = list(pedido.get("historico") or [])

        descricao = (
            f"Status alterado de "
            f"{cls._descricao_status(status_anterior)} "
            f"para {cls._descricao_status(novo_status)}"
        )

        motivo = "Cancelado pela equipe interna" if novo_status == cls.STATUS_CANCELADO else ""

        historico.append(
            cls._novo_evento_historico(
                tipo="ALTERACAO_STATUS",
                descricao=descricao,
                usuario_tipo="INTERNO",
                usuario_nome=usuario_nome,
                status_anterior=status_anterior,
                status_novo=novo_status,
                motivo=motivo,
            )
        )

        payload = {
            "status": novo_status,
            "atualizado_em": agora,
            "status_atualizado_por": cls._texto(usuario_nome),
            "status_atualizado_por_nome": cls._texto(usuario_nome),
            "historico": historico,
        }

        if novo_status == cls.STATUS_CANCELADO:
            payload["cancelado_em"] = agora

            if not pedido.get("motivo_cancelamento"):
                payload["motivo_cancelamento"] = "Cancelado pela equipe interna"

        cls._collection(cls.COLLECTION_PEDIDOS).document(pedido_id).update(payload)

        AuditoriaService.registrar_status_pedido(
            pedido_id=pedido_id,
            codigo_pedido=pedido.get("codigo_pedido"),
            status_anterior=status_anterior,
            status_novo=novo_status,
            usuario_nome=usuario_nome,
            origem="INTERNO",
        )

        pedido_atualizado = cls.buscar_pedido_por_id(pedido_id)

        return True, "Status atualizado com sucesso.", pedido_atualizado

    @classmethod
    def simular_pagamento_pedido(cls, pedido_id, resultado, usuario_nome):
        pedido = cls.buscar_pedido_por_id(pedido_id)

        if not pedido:
            return False, "Pedido não encontrado.", None

        if pedido.get("fechado_em_caixa"):
            fechamento = pedido.get("fechamento_caixa") or {}
            return (
                False,
                f"Pedido bloqueado. Ele já faz parte do fechamento de caixa {fechamento.get('id', '')}.",
                pedido,
            )

        if pedido.get("status") in [cls.STATUS_CANCELADO, cls.STATUS_ENTREGUE]:
            return False, "Este pedido não permite mais simulação de pagamento.", pedido

        resultado = cls._texto(resultado).upper()

        if resultado not in [cls.PAGAMENTO_PAGO, cls.PAGAMENTO_RECUSADO]:
            return False, "Resultado de pagamento inválido.", pedido

        pagamento_anterior = pedido.get("pagamento_status")

        agora = cls._agora_iso()
        historico = list(pedido.get("historico") or [])

        descricao = (
            "Pagamento confirmado pela equipe interna"
            if resultado == cls.PAGAMENTO_PAGO
            else "Pagamento recusado na simulação interna"
        )

        historico.append(
            cls._novo_evento_historico(
                tipo="PAGAMENTO",
                descricao=descricao,
                usuario_tipo="INTERNO",
                usuario_nome=usuario_nome,
                status_anterior=pagamento_anterior,
                status_novo=resultado,
                motivo="Simulação de pagamento no painel interno",
            )
        )

        payload = {
            "pagamento_status": resultado,
            "situacao_pagamento": cls.PAGAMENTO_PAGO if resultado == cls.PAGAMENTO_PAGO else cls.PAGAMENTO_RECUSADO,
            "pagamento_status_descricao": cls._descricao_pagamento(resultado),
            "pagamento_metodo": pedido.get("pagamento_metodo"),
            "pagamento_metodo_descricao": pedido.get("pagamento_metodo_descricao"),
            "forma_pagamento": pedido.get("pagamento_metodo"),
            "pagamento_valor": pedido.get("valor_total") or 0,
            "pagamento_valor_formatado": cls._formatar_moeda(pedido.get("valor_total") or 0),
            "pagamento_transacao_id": f"SIM-{pedido_id[:8].upper()}",
            "atualizado_em": agora,
            "historico": historico,
        }

        if resultado == cls.PAGAMENTO_PAGO:
            payload["pago_em"] = agora
        else:
            payload["pago_em"] = ""

        cls._collection(cls.COLLECTION_PEDIDOS).document(pedido_id).update(payload)

        AuditoriaService.registrar_pagamento(
            pedido_id=pedido_id,
            codigo_pedido=pedido.get("codigo_pedido"),
            pagamento_anterior=pagamento_anterior,
            pagamento_novo=resultado,
            usuario_nome=usuario_nome,
            origem="INTERNO",
        )

        pedido_atualizado = cls.buscar_pedido_por_id(pedido_id)

        return True, "Pagamento atualizado com sucesso.", pedido_atualizado