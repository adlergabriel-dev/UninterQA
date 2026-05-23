from datetime import datetime

from services.firebase_service import FirebaseService
from services.cliente_service import ClienteService
from services.unidade_service import UnidadeService
from services.auditoria_service import AuditoriaService


class PedidoService:
    COLECAO = "pedidos"

    STATUS_AGUARDANDO_PAGAMENTO = "AGUARDANDO_PAGAMENTO"
    STATUS_PAGO = "PAGO"
    STATUS_EM_PREPARO = "EM_PREPARO"
    STATUS_PRONTO_PARA_RETIRADA = "PRONTO_PARA_RETIRADA"
    STATUS_SAIU_PARA_ENTREGA = "SAIU_PARA_ENTREGA"
    STATUS_CONCLUIDO = "CONCLUIDO"
    STATUS_CANCELADO = "CANCELADO"

    PAGAMENTO_PENDENTE = "PENDENTE"
    PAGAMENTO_APROVADO = "APROVADO"
    PAGAMENTO_RECUSADO = "RECUSADO"
    PAGAMENTO_EXPIRADO = "EXPIRADO"

    TRANSICOES_VALIDAS = {
        STATUS_AGUARDANDO_PAGAMENTO: [STATUS_PAGO, STATUS_CANCELADO],
        STATUS_PAGO: [STATUS_EM_PREPARO, STATUS_CANCELADO],
        STATUS_EM_PREPARO: [STATUS_PRONTO_PARA_RETIRADA, STATUS_SAIU_PARA_ENTREGA, STATUS_CANCELADO],
        STATUS_PRONTO_PARA_RETIRADA: [STATUS_CONCLUIDO],
        STATUS_SAIU_PARA_ENTREGA: [STATUS_CONCLUIDO],
        STATUS_CONCLUIDO: [],
        STATUS_CANCELADO: [],
    }

    @classmethod
    def _collection(cls):
        return FirebaseService.get_collection(cls.COLECAO)

    @classmethod
    def _texto(cls, valor):
        return str(valor or "").strip()

    @classmethod
    def _texto_upper(cls, valor):
        return cls._texto(valor).upper()

    @classmethod
    def _bool(cls, valor, default=False):
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
    def _descricao_status(cls, status):
        mapa = {
            cls.STATUS_AGUARDANDO_PAGAMENTO: "Aguardando pagamento",
            cls.STATUS_PAGO: "Pago",
            cls.STATUS_EM_PREPARO: "Em preparo",
            cls.STATUS_PRONTO_PARA_RETIRADA: "Pronto para retirada",
            cls.STATUS_SAIU_PARA_ENTREGA: "Saiu para entrega",
            cls.STATUS_CONCLUIDO: "Concluído",
            cls.STATUS_CANCELADO: "Cancelado",
        }
        return mapa.get(cls._texto_upper(status), cls._texto(status))

    @classmethod
    def _descricao_pagamento(cls, status):
        mapa = {
            cls.PAGAMENTO_PENDENTE: "Pendente",
            cls.PAGAMENTO_APROVADO: "Aprovado",
            cls.PAGAMENTO_RECUSADO: "Recusado",
            cls.PAGAMENTO_EXPIRADO: "Expirado",
        }
        return mapa.get(cls._texto_upper(status), cls._texto(status))

    @classmethod
    def listar(cls):
        docs = cls._collection().stream()
        resultado = []

        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id

            valor_total = float(item.get("valor_total") or 0)
            item["valor_total_formatado"] = cls._formatar_moeda(valor_total)
            item["status_descricao"] = cls._descricao_status(item.get("status"))
            item["pagamento_status_descricao"] = cls._descricao_pagamento(item.get("pagamento_status"))

            resultado.append(item)

        resultado.sort(key=lambda x: x.get("criado_em", ""), reverse=True)
        return resultado

    @classmethod
    def buscar_por_id(cls, pedido_id: str):
        doc_ref = cls._collection().document(pedido_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = doc.id

        valor_subtotal = float(data.get("valor_subtotal") or 0)
        valor_total = float(data.get("valor_total") or 0)

        data["valor_subtotal_formatado"] = cls._formatar_moeda(valor_subtotal)
        data["valor_total_formatado"] = cls._formatar_moeda(valor_total)
        data["status_descricao"] = cls._descricao_status(data.get("status"))
        data["pagamento_status_descricao"] = cls._descricao_pagamento(data.get("pagamento_status"))

        return data

    @classmethod
    def listar_itens(cls, pedido_id: str):
        docs = (
            cls._collection()
            .document(pedido_id)
            .collection("itens")
            .stream()
        )

        itens = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id

            item["preco_unitario_formatado"] = cls._formatar_moeda(item.get("preco_unitario"))
            item["subtotal_formatado"] = cls._formatar_moeda(item.get("subtotal"))

            itens.append(item)

        return itens

    @classmethod
    def listar_historico_status(cls, pedido_id: str):
        docs = (
            cls._collection()
            .document(pedido_id)
            .collection("historico_status")
            .stream()
        )

        historico = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id
            historico.append(item)

        historico.sort(key=lambda x: x.get("data_evento", ""), reverse=True)
        return historico

    @classmethod
    def listar_pagamentos(cls, pedido_id: str):
        docs = (
            cls._collection()
            .document(pedido_id)
            .collection("pagamentos")
            .stream()
        )

        pagamentos = []
        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id
            pagamentos.append(item)

        pagamentos.sort(key=lambda x: x.get("criado_em", ""), reverse=True)
        return pagamentos

    @classmethod
    def gerar_codigo_pedido(cls):
        agora = datetime.utcnow()
        return agora.strftime("PED-%Y%m%d-%H%M%S")

    @classmethod
    def gerar_transacao_pagamento(cls):
        agora = datetime.utcnow()
        return agora.strftime("TXN-%Y%m%d-%H%M%S")

    @classmethod
    def buscar_item_cardapio(cls, unidade_id: str, produto_id: str):
        docs = (
            FirebaseService.get_collection("cardapio_unidade")
            .where("unidade_id", "==", unidade_id)
            .where("produto_id", "==", produto_id)
            .where("ativo", "==", True)
            .stream()
        )

        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data

        return None

    @classmethod
    def criar_pedido_simples(cls, dados: dict):
        cliente_id = cls._texto(dados.get("cliente_id"))
        unidade_id = cls._texto(dados.get("unidade_id"))
        produto_id = cls._texto(dados.get("produto_id"))
        observacao = cls._texto(dados.get("observacao"))

        try:
            quantidade = int(dados.get("quantidade", 1) or 1)
        except Exception:
            quantidade = 0

        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")

        cliente = ClienteService.buscar_por_id(cliente_id)
        if not cliente:
            raise ValueError("Cliente não encontrado.")

        if not cliente.get("ativo", False):
            raise ValueError("Cliente inativo não pode gerar pedido.")

        unidade = UnidadeService.buscar_por_id(unidade_id)
        if not unidade:
            raise ValueError("Unidade não encontrada.")

        if not unidade.get("ativo", False):
            raise ValueError("Unidade inativa não pode receber pedido.")

        item_cardapio = cls.buscar_item_cardapio(unidade_id, produto_id)
        if not item_cardapio:
            raise ValueError("Produto não vinculado ao cardápio da unidade.")

        if not item_cardapio.get("disponivel", False):
            raise ValueError("Produto indisponível para esta unidade.")

        preco_unitario = float(item_cardapio.get("preco_venda", 0))
        subtotal = round(preco_unitario * quantidade, 2)
        total = subtotal
        agora = cls._agora_iso()

        codigo_pedido = cls.gerar_codigo_pedido()

        pedido_payload = {
            "codigo_pedido": codigo_pedido,
            "cliente_id": cliente_id,
            "cliente_nome": cliente.get("nome", ""),
            "unidade_id": unidade_id,
            "unidade_nome": unidade.get("nome", ""),
            "canal_origem": "WEB",
            "status": cls.STATUS_AGUARDANDO_PAGAMENTO,
            "pagamento_status": cls.PAGAMENTO_PENDENTE,
            "valor_subtotal": subtotal,
            "valor_desconto": 0,
            "valor_total": total,
            "observacao": observacao,
            "ativo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        }

        pedido_ref = cls._collection().document()
        pedido_ref.set(pedido_payload)

        item_payload = {
            "produto_id": produto_id,
            "nome_produto_snapshot": item_cardapio.get("nome_produto", ""),
            "imagem_url_snapshot": item_cardapio.get("imagem_url", ""),
            "preco_unitario": preco_unitario,
            "quantidade": quantidade,
            "subtotal": subtotal,
        }

        pedido_ref.collection("itens").document().set(item_payload)

        historico_payload = {
            "status_anterior": "",
            "status_novo": cls.STATUS_AGUARDANDO_PAGAMENTO,
            "origem": "WEB",
            "observacao": "Pedido criado",
            "data_evento": agora,
        }

        pedido_ref.collection("historico_status").document().set(historico_payload)

        pagamento_payload = {
            "metodo": "PIX_FAKE",
            "status": cls.PAGAMENTO_PENDENTE,
            "valor": total,
            "simulado": True,
            "resultado_simulado": "",
            "transacao_id": cls.gerar_transacao_pagamento(),
            "criado_em": agora,
            "atualizado_em": agora,
        }

        pedido_ref.collection("pagamentos").document().set(pagamento_payload)

        AuditoriaService.registrar(
            entidade="PEDIDO",
            entidade_id=pedido_ref.id,
            acao="CRIACAO",
            descricao="Pedido criado com status AGUARDANDO_PAGAMENTO",
            origem="WEB",
            dados_antes={},
            dados_depois={
                "status": cls.STATUS_AGUARDANDO_PAGAMENTO,
                "pagamento_status": cls.PAGAMENTO_PENDENTE,
                "valor_total": total,
            },
        )

        return pedido_ref.id

    @classmethod
    def listar_proximos_status(cls, status_atual: str):
        return cls.TRANSICOES_VALIDAS.get(cls._texto_upper(status_atual), [])

    @classmethod
    def alterar_status(cls, pedido_id: str, novo_status: str, observacao: str = ""):
        pedido = cls.buscar_por_id(pedido_id)

        if not pedido:
            raise ValueError("Pedido não encontrado.")

        status_atual = cls._texto_upper(pedido.get("status"))
        novo_status = cls._texto_upper(novo_status)
        proximos = cls.listar_proximos_status(status_atual)

        if status_atual == cls.STATUS_CANCELADO:
            raise ValueError("Pedido cancelado não pode ter status alterado.")

        if status_atual == cls.STATUS_CONCLUIDO:
            raise ValueError("Pedido concluído não pode ter status alterado.")

        if novo_status not in proximos:
            raise ValueError(f"Transição inválida: {status_atual} não pode ir para {novo_status}.")

        agora = cls._agora_iso()

        cls._collection().document(pedido_id).update({
            "status": novo_status,
            "atualizado_em": agora,
        })

        historico_payload = {
            "status_anterior": status_atual,
            "status_novo": novo_status,
            "origem": "WEB",
            "observacao": cls._texto(observacao),
            "data_evento": agora,
        }

        (
            cls._collection()
            .document(pedido_id)
            .collection("historico_status")
            .document()
            .set(historico_payload)
        )

        AuditoriaService.registrar(
            entidade="PEDIDO",
            entidade_id=pedido_id,
            acao="ALTERACAO_STATUS",
            descricao=f"Pedido alterado de {status_atual} para {novo_status}",
            origem="WEB",
            dados_antes={"status": status_atual},
            dados_depois={"status": novo_status},
        )

    @classmethod
    def simular_pagamento(cls, pedido_id: str, resultado: str):
        resultado = cls._texto_upper(resultado)

        if resultado not in [
            cls.PAGAMENTO_APROVADO,
            cls.PAGAMENTO_RECUSADO,
            cls.PAGAMENTO_PENDENTE,
            cls.PAGAMENTO_EXPIRADO,
        ]:
            raise ValueError("Resultado de pagamento inválido.")

        pedido = cls.buscar_por_id(pedido_id)
        if not pedido:
            raise ValueError("Pedido não encontrado.")

        status_atual = cls._texto_upper(pedido.get("status"))
        pagamento_status_atual = cls._texto_upper(pedido.get("pagamento_status"))

        if status_atual in [cls.STATUS_CONCLUIDO, cls.STATUS_CANCELADO]:
            raise ValueError("Não é possível simular pagamento para pedido encerrado.")

        if pagamento_status_atual == cls.PAGAMENTO_APROVADO:
            raise ValueError("Este pedido já possui pagamento aprovado.")

        pagamentos = cls.listar_pagamentos(pedido_id)
        if not pagamentos:
            raise ValueError("Nenhum pagamento encontrado para este pedido.")

        pagamento = pagamentos[0]
        pagamento_id = pagamento["id"]

        agora = cls._agora_iso()
        novo_status_pedido = status_atual
        observacao_historico = ""

        if resultado == cls.PAGAMENTO_APROVADO:
            novo_status_pedido = cls.STATUS_PAGO
            observacao_historico = "Pagamento simulado como APROVADO"
        elif resultado == cls.PAGAMENTO_RECUSADO:
            novo_status_pedido = cls.STATUS_CANCELADO
            observacao_historico = "Pagamento simulado como RECUSADO"
        elif resultado == cls.PAGAMENTO_PENDENTE:
            novo_status_pedido = status_atual
            observacao_historico = "Pagamento simulado como PENDENTE"
        elif resultado == cls.PAGAMENTO_EXPIRADO:
            novo_status_pedido = cls.STATUS_CANCELADO
            observacao_historico = "Pagamento simulado como EXPIRADO"

        (
            cls._collection()
            .document(pedido_id)
            .collection("pagamentos")
            .document(pagamento_id)
            .update({
                "status": resultado,
                "resultado_simulado": resultado,
                "atualizado_em": agora,
            })
        )

        cls._collection().document(pedido_id).update({
            "pagamento_status": resultado,
            "status": novo_status_pedido,
            "atualizado_em": agora,
        })

        AuditoriaService.registrar(
            entidade="PAGAMENTO",
            entidade_id=pagamento_id,
            acao="SIMULACAO_PAGAMENTO",
            descricao=f"Pagamento simulado com resultado {resultado}",
            origem="WEB",
            dados_antes={"status": pagamento.get("status", "")},
            dados_depois={"status": resultado},
        )

        if novo_status_pedido != status_atual:
            historico_payload = {
                "status_anterior": status_atual,
                "status_novo": novo_status_pedido,
                "origem": "WEB",
                "observacao": observacao_historico,
                "data_evento": agora,
            }

            (
                cls._collection()
                .document(pedido_id)
                .collection("historico_status")
                .document()
                .set(historico_payload)
            )

            AuditoriaService.registrar(
                entidade="PEDIDO",
                entidade_id=pedido_id,
                acao="ALTERACAO_STATUS",
                descricao=f"Pedido alterado de {status_atual} para {novo_status_pedido} por simulação de pagamento",
                origem="WEB",
                dados_antes={"status": status_atual},
                dados_depois={"status": novo_status_pedido, "pagamento_status": resultado},
            )