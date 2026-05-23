from datetime import datetime
from uuid import uuid4

from services.firebase_service import FirebaseService


class ClientePedidoService:
    COLLECTION_CLIENTES = "clientes"
    COLLECTION_UNIDADES = "unidades"
    COLLECTION_PRODUTOS = "produtos"
    COLLECTION_CARDAPIO = "cardapio_unidade"
    COLLECTION_PEDIDOS = "pedidos"

    ORIGEM_CLIENTE_WEB = "CLIENTE_WEB"

    STATUS_ABERTO = "ABERTO"
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

    STATUS_CANCELAVEIS = {STATUS_ABERTO}

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
    def _agora_ord(cls):
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _agora_texto(cls):
        return datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

    @classmethod
    def _formatar_moeda(cls, valor):
        return f"R$ {float(valor or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @classmethod
    def _normalizar_status(cls, status):
        status = cls._texto(status).upper()

        if status == "CRIADO":
            return cls.STATUS_ABERTO

        if status in {
            cls.STATUS_ABERTO,
            cls.STATUS_EM_PREPARO,
            cls.STATUS_PRONTO,
            cls.STATUS_ENVIADO,
            cls.STATUS_ENTREGUE,
            cls.STATUS_FINALIZADO,
            cls.STATUS_CANCELADO,
        }:
            return status

        return cls.STATUS_ABERTO

    @classmethod
    def _normalizar_pagamento(cls, status):
        status = cls._texto(status).upper()

        if status in [
            cls.PAGAMENTO_AGUARDANDO,
            cls.PAGAMENTO_PENDENTE,
            cls.PAGAMENTO_PAGO,
            cls.PAGAMENTO_RECUSADO,
            "CANCELADO",
            "ESTORNADO",
        ]:
            return status

        return cls.PAGAMENTO_PENDENTE

    @classmethod
    def _descricao_status(cls, status):
        status = cls._normalizar_status(status)

        mapa = {
            cls.STATUS_ABERTO: "Aberto",
            cls.STATUS_EM_PREPARO: "Em preparo",
            cls.STATUS_PRONTO: "Pronto",
            cls.STATUS_ENVIADO: "Enviado",
            cls.STATUS_ENTREGUE: "Entregue",
            cls.STATUS_FINALIZADO: "Finalizado",
            cls.STATUS_CANCELADO: "Cancelado",
        }

        return mapa.get(status, "Aberto")

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
    def _status_cliente(cls, status, pagamento_status):
        status = cls._normalizar_status(status)
        pagamento_status = cls._normalizar_pagamento(pagamento_status)

        if status == cls.STATUS_CANCELADO:
            return {
                "codigo": "cancelado",
                "descricao": "Cancelado",
                "mensagem": "Este pedido foi cancelado.",
                "etapa": 0,
            }

        if pagamento_status != cls.PAGAMENTO_PAGO:
            return {
                "codigo": "aguardando-pagamento",
                "descricao": "Aguardando pagamento",
                "mensagem": "Seu pedido foi recebido e está aguardando a confirmação do pagamento.",
                "etapa": 1,
            }

        if status == cls.STATUS_ABERTO:
            return {
                "codigo": "confirmado",
                "descricao": "Pedido confirmado",
                "mensagem": "Pagamento confirmado. Seu pedido já foi enviado para produção.",
                "etapa": 2,
            }

        if status == cls.STATUS_EM_PREPARO:
            return {
                "codigo": "em-preparo",
                "descricao": "Em preparo",
                "mensagem": "Seu pedido está sendo preparado.",
                "etapa": 3,
            }

        if status in [cls.STATUS_PRONTO, cls.STATUS_ENVIADO]:
            return {
                "codigo": "saiu-para-entrega",
                "descricao": "Saiu para entrega",
                "mensagem": "Seu pedido está pronto e saiu para entrega.",
                "etapa": 4,
            }

        if status in [cls.STATUS_ENTREGUE, cls.STATUS_FINALIZADO]:
            return {
                "codigo": "finalizado",
                "descricao": "Finalizado",
                "mensagem": "Pedido finalizado. Obrigado pela preferência!",
                "etapa": 5,
            }

        return {
            "codigo": "confirmado",
            "descricao": "Pedido confirmado",
            "mensagem": "Seu pedido está em andamento.",
            "etapa": 2,
        }

    @classmethod
    def _pode_cancelar(cls, status, pagamento_status=None):
        status = cls._normalizar_status(status)
        pagamento_status = cls._normalizar_pagamento(pagamento_status)

        if status != cls.STATUS_ABERTO:
            return False

        if pagamento_status == cls.PAGAMENTO_PAGO:
            return False

        return True

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
    def _descricao_historico_cliente(cls, evento):
        evento = evento or {}

        tipo = cls._texto(evento.get("tipo")).upper()
        descricao = cls._texto(evento.get("descricao"))
        status_novo = cls._normalizar_status(evento.get("status_novo"))
        motivo = cls._texto(evento.get("motivo"))

        if tipo == "CRIACAO":
            return {
                "titulo": "Pedido recebido",
                "descricao": "Seu pedido foi registrado com sucesso.",
            }

        if tipo == "PAGAMENTO":
            if status_novo == cls.PAGAMENTO_PAGO or cls._texto(evento.get("status_novo")).upper() == cls.PAGAMENTO_PAGO:
                return {
                    "titulo": "Pagamento confirmado",
                    "descricao": "O pagamento do seu pedido foi confirmado.",
                }

            if cls._texto(evento.get("status_novo")).upper() == cls.PAGAMENTO_RECUSADO:
                return {
                    "titulo": "Pagamento recusado",
                    "descricao": "O pagamento do pedido não foi aprovado.",
                }

            return {
                "titulo": "Atualização do pagamento",
                "descricao": descricao or "Houve uma atualização no pagamento do pedido.",
            }

        if tipo in ["ALTERACAO_STATUS", "STATUS", "ALTERACAO"]:
            if status_novo == cls.STATUS_EM_PREPARO:
                return {
                    "titulo": "Pedido em preparo",
                    "descricao": "Seu pedido foi enviado para preparo.",
                }

            if status_novo in [cls.STATUS_PRONTO, cls.STATUS_ENVIADO]:
                return {
                    "titulo": "Pedido saiu para entrega",
                    "descricao": "Seu pedido está pronto e saiu para entrega.",
                }

            if status_novo in [cls.STATUS_ENTREGUE, cls.STATUS_FINALIZADO]:
                return {
                    "titulo": "Pedido finalizado",
                    "descricao": "Seu pedido foi finalizado. Obrigado pela preferência!",
                }

            if status_novo == cls.STATUS_CANCELADO:
                return {
                    "titulo": "Pedido cancelado",
                    "descricao": motivo or "O pedido foi cancelado.",
                }

        if tipo == "CANCELAMENTO":
            return {
                "titulo": "Pedido cancelado",
                "descricao": motivo or descricao or "O pedido foi cancelado.",
            }

        return {
            "titulo": "Atualização do pedido",
            "descricao": descricao or "Houve uma atualização no seu pedido.",
        }

    @classmethod
    def _normalizar_historico_cliente(cls, historico):
        historico = historico or []

        if not isinstance(historico, list):
            return []

        eventos_cliente = []

        for evento in historico:
            if not isinstance(evento, dict):
                continue

            textos = cls._descricao_historico_cliente(evento)

            eventos_cliente.append({
                "data": cls._texto(evento.get("criado_em")),
                "titulo": textos["titulo"],
                "descricao": textos["descricao"],
                "tipo": cls._texto(evento.get("tipo")).upper(),
            })

        eventos_cliente.sort(
            key=lambda x: cls._texto(x.get("data")),
            reverse=True
        )

        return eventos_cliente

    @classmethod
    def buscar_cliente_por_id(cls, cliente_id):
        if not cliente_id:
            return None

        doc = cls._collection(cls.COLLECTION_CLIENTES).document(cliente_id).get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = doc.id

        return {
            "id": data["id"],
            "nome": cls._texto(data.get("nome")),
            "telefone": cls._texto(data.get("telefone")),
            "email": cls._texto_lower(data.get("email")),
            "cpf": cls._texto(data.get("cpf")),
            "ativo": cls._bool(data.get("ativo"), True),
        }

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
    def _mapear_produtos_ativos(cls):
        docs = cls._collection(cls.COLLECTION_PRODUTOS).stream()
        produtos = {}

        for doc in docs:
            data = doc.to_dict() or {}

            if not cls._bool(data.get("ativo"), True):
                continue

            produtos[doc.id] = {
                "id": doc.id,
                "nome": cls._texto(data.get("nome")),
                "descricao": cls._texto(data.get("descricao")),
                "imagem_url": cls._texto(data.get("imagem_url") or data.get("imagem")),
            }

        return produtos

    @classmethod
    def _mapear_unidades_ativas(cls):
        docs = cls._collection(cls.COLLECTION_UNIDADES).stream()
        unidades = {}

        for doc in docs:
            data = doc.to_dict() or {}

            if not cls._bool(data.get("ativo"), True):
                continue

            unidades[doc.id] = {
                "id": doc.id,
                "nome": cls._texto(data.get("nome")),
            }

        return unidades

    @classmethod
    def _listar_cardapio_ativo(cls):
        docs = cls._collection(cls.COLLECTION_CARDAPIO).stream()
        itens = []

        for doc in docs:
            data = doc.to_dict() or {}

            if not cls._bool(data.get("ativo"), True):
                continue

            itens.append({
                "id": doc.id,
                "unidade_id": cls._texto(
                    data.get("unidade_id")
                    or data.get("id_unidade")
                    or data.get("unidadeId")
                ),
                "produto_id": cls._texto(
                    data.get("produto_id")
                    or data.get("id_produto")
                    or data.get("produtoId")
                ),
                "nome_unidade": cls._texto(data.get("nome_unidade")),
                "nome_produto": cls._texto(data.get("nome_produto")),
                "descricao_produto": cls._texto(data.get("descricao_produto")),
                "imagem_url": cls._texto(data.get("imagem_url") or data.get("imagem")),
                "preco": data.get("preco"),
                "preco_venda": data.get("preco_venda"),
            })

        return itens

    @classmethod
    def listar_itens_por_unidade(cls, unidade_id):
        unidade_id = cls._texto(unidade_id)

        if not unidade_id:
            return []

        produtos_map = cls._mapear_produtos_ativos()
        unidades_map = cls._mapear_unidades_ativas()
        unidade = unidades_map.get(unidade_id)

        itens = []

        for item in cls._listar_cardapio_ativo():
            if item["unidade_id"] != unidade_id:
                continue

            produto = produtos_map.get(item["produto_id"])

            nome_produto = cls._texto(
                (produto or {}).get("nome")
                or item.get("nome_produto")
            )

            descricao_produto = cls._texto(
                (produto or {}).get("descricao")
                or item.get("descricao_produto")
            )

            imagem_url = cls._texto(
                (produto or {}).get("imagem_url")
                or item.get("imagem_url")
            )

            nome_unidade = cls._texto(
                (unidade or {}).get("nome")
                or item.get("nome_unidade")
            )

            if not nome_produto:
                continue

            preco = item.get("preco")

            if preco in [None, ""]:
                preco = item.get("preco_venda")

            try:
                preco = float(preco) if preco not in [None, ""] else 0.0
            except Exception:
                preco = 0.0

            itens.append({
                "cardapio_id": item["id"],
                "unidade_id": unidade_id,
                "unidade_nome": nome_unidade,
                "produto_id": item["produto_id"],
                "produto_nome": nome_produto,
                "produto_descricao": descricao_produto,
                "imagem_url": imagem_url,
                "preco": preco,
                "preco_formatado": cls._formatar_moeda(preco),
            })

        itens.sort(key=lambda x: cls._texto_lower(x.get("produto_nome")))
        return itens

    @classmethod
    def criar_pedido(cls, cliente_id, unidade_id, itens_form):
        cliente_id = cls._texto(cliente_id)
        unidade_id = cls._texto(unidade_id)
        pagamento_metodo = cls._texto(itens_form.get("pagamento_metodo")).upper()

        if not cliente_id:
            return False, "Cliente inválido.", None

        if not unidade_id:
            return False, "Selecione a filial.", None

        if pagamento_metodo not in ["PIX", "CARTAO", "DINHEIRO"]:
            return False, "Selecione uma forma de pagamento.", None

        cliente = cls.buscar_cliente_por_id(cliente_id)

        if not cliente:
            return False, "Cliente não encontrado.", None

        unidades_map = cls._mapear_unidades_ativas()
        unidade = unidades_map.get(unidade_id)

        if not unidade:
            return False, "Filial inválida.", None

        produtos_disponiveis = cls.listar_itens_por_unidade(unidade_id)
        produtos_map = {item["produto_id"]: item for item in produtos_disponiveis}

        itens_pedido = []
        total_geral = 0.0
        quantidade_total_itens = 0

        for produto_id, produto in produtos_map.items():
            quantidade_raw = itens_form.get(f"quantidade__{produto_id}")
            observacao = cls._texto(itens_form.get(f"observacao__{produto_id}"))

            try:
                quantidade = int(quantidade_raw or 0)
            except Exception:
                quantidade = 0

            if quantidade <= 0:
                continue

            preco_unitario = float(produto.get("preco") or 0.0)
            subtotal = preco_unitario * quantidade

            total_geral += subtotal
            quantidade_total_itens += quantidade

            itens_pedido.append({
                "cardapio_id": produto.get("cardapio_id"),
                "produto_id": produto["produto_id"],
                "nome": produto["produto_nome"],
                "produto_nome": produto["produto_nome"],
                "descricao": produto.get("produto_descricao", ""),
                "produto_descricao": produto.get("produto_descricao", ""),
                "imagem_url": produto.get("imagem_url", ""),
                "quantidade": quantidade,
                "observacao": observacao,
                "valor_unitario": round(preco_unitario, 2),
                "preco_unitario": round(preco_unitario, 2),
                "preco_unitario_formatado": cls._formatar_moeda(preco_unitario),
                "valor_total": round(subtotal, 2),
                "subtotal": round(subtotal, 2),
                "subtotal_formatado": cls._formatar_moeda(subtotal),
                "snapshot_produto": {
                    "nome": produto["produto_nome"],
                    "produto_nome": produto["produto_nome"],
                    "descricao": produto["produto_descricao"],
                    "produto_descricao": produto["produto_descricao"],
                    "imagem_url": produto["imagem_url"],
                    "preco": preco_unitario,
                    "preco_unitario": preco_unitario,
                    "preco_formatado": cls._formatar_moeda(preco_unitario),
                    "unidade_id": produto["unidade_id"],
                    "unidade_nome": produto["unidade_nome"],
                    "cardapio_id": produto["cardapio_id"],
                    "produto_id": produto["produto_id"],
                },
            })

        if not itens_pedido:
            return False, "Adicione pelo menos um item ao pedido.", None

        pedido_id = str(uuid4())
        agora = cls._agora_iso()
        agora_ord = cls._agora_ord()
        agora_texto = cls._agora_texto()

        historico = [
            cls._novo_evento_historico(
                tipo="CRIACAO",
                descricao=f"Pedido criado pelo cliente. Forma de pagamento escolhida: {pagamento_metodo}",
                usuario_tipo="CLIENTE",
                usuario_nome=cliente["nome"] or cliente["email"],
                status_anterior="",
                status_novo=cls.STATUS_ABERTO,
            )
        ]

        payload = {
            "codigo_pedido": pedido_id[:8].upper(),
            "origem": cls.ORIGEM_CLIENTE_WEB,
            "tipo": cls.ORIGEM_CLIENTE_WEB,
            "canal": cls.ORIGEM_CLIENTE_WEB,

            "cliente_id": cliente["id"],
            "cliente_nome": cliente["nome"],
            "cliente_email": cliente["email"],
            "cliente_telefone": cliente["telefone"],

            "unidade_id": unidade["id"],
            "unidade_nome": unidade["nome"],

            "status": cls.STATUS_ABERTO,

            "situacao_pagamento": cls.PAGAMENTO_PENDENTE,
            "pagamento_status": cls.PAGAMENTO_AGUARDANDO,
            "pagamento_status_descricao": cls._descricao_pagamento(cls.PAGAMENTO_AGUARDANDO),

            "forma_pagamento": pagamento_metodo,
            "pagamento_metodo": pagamento_metodo,
            "pagamento_metodo_descricao": pagamento_metodo,

            "pagamento_valor": round(total_geral, 2),
            "pagamento_valor_formatado": cls._formatar_moeda(total_geral),
            "pagamento_transacao_id": "",
            "pago_em": "",

            "itens": itens_pedido,
            "quantidade_itens": len(itens_pedido),
            "quantidade_total_itens": quantidade_total_itens,

            "subtotal": round(total_geral, 2),
            "total": round(total_geral, 2),

            "valor_produtos": round(total_geral, 2),
            "valor_desconto": 0.0,
            "valor_entrega": 0.0,
            "valor_total": round(total_geral, 2),
            "valor_total_formatado": cls._formatar_moeda(total_geral),

            "criado_em": agora,
            "criado_em_texto": agora_texto,
            "criado_em_ord": agora_ord,

            "atualizado_em": agora,
            "atualizado_em_texto": agora_texto,

            "cancelado_em": "",
            "motivo_cancelamento": "",
            "historico": historico,
        }

        cls._collection(cls.COLLECTION_PEDIDOS).document(pedido_id).set(payload)

        return True, "Pedido criado com sucesso.", pedido_id

    @classmethod
    def buscar_item_disponivel(cls, unidade_id, produto_id):
        unidade_id = cls._texto(unidade_id)
        produto_id = cls._texto(produto_id)

        if not unidade_id or not produto_id:
            return None

        produtos = cls.listar_itens_por_unidade(unidade_id)

        for produto in produtos:
            if produto.get("produto_id") == produto_id:
                return produto

        return None

    @classmethod
    def montar_item_carrinho(cls, unidade_id, produto_id, quantidade, observacao=""):
        unidade_id = cls._texto(unidade_id)
        produto_id = cls._texto(produto_id)
        observacao = cls._texto(observacao)

        try:
            quantidade = int(quantidade or 1)
        except Exception:
            quantidade = 1

        if quantidade <= 0:
            return False, "Informe uma quantidade válida.", None

        produto = cls.buscar_item_disponivel(unidade_id, produto_id)

        if not produto:
            return False, "Produto indisponível para esta filial.", None

        preco_unitario = float(produto.get("preco") or 0.0)
        subtotal = preco_unitario * quantidade

        item = {
            "cardapio_id": produto.get("cardapio_id"),
            "unidade_id": produto.get("unidade_id"),
            "unidade_nome": produto.get("unidade_nome"),

            "produto_id": produto.get("produto_id"),
            "produto_nome": produto.get("produto_nome"),
            "produto_descricao": produto.get("produto_descricao"),

            # IMPORTANTE:
            # Não salvar imagem base64 na sessão.
            "imagem_url": "",

            "quantidade": quantidade,
            "observacao": observacao,

            "preco_unitario": round(preco_unitario, 2),
            "valor_unitario": round(preco_unitario, 2),
            "preco_unitario_formatado": cls._formatar_moeda(preco_unitario),

            "subtotal": round(subtotal, 2),
            "valor_total": round(subtotal, 2),
            "subtotal_formatado": cls._formatar_moeda(subtotal),
        }

        return True, "Item montado com sucesso.", item

    @classmethod
    def normalizar_carrinho(cls, carrinho):
        carrinho = carrinho or {}

        itens = carrinho.get("itens") or []
        itens_normalizados = []

        total = 0.0
        quantidade_total_itens = 0

        unidade_id = cls._texto(carrinho.get("unidade_id"))
        unidade_nome = cls._texto(carrinho.get("unidade_nome"))

        for item in itens:
            if not isinstance(item, dict):
                continue

            produto_id = cls._texto(item.get("produto_id"))

            if not produto_id:
                continue

            try:
                quantidade = int(item.get("quantidade") or 0)
            except Exception:
                quantidade = 0

            if quantidade <= 0:
                continue

            try:
                preco_unitario = float(
                    item.get("preco_unitario")
                    or item.get("valor_unitario")
                    or 0.0
                )
            except Exception:
                preco_unitario = 0.0

            subtotal = preco_unitario * quantidade
            total += subtotal
            quantidade_total_itens += quantidade

            item_normalizado = {
                "cardapio_id": cls._texto(item.get("cardapio_id")),
                "unidade_id": cls._texto(item.get("unidade_id") or unidade_id),
                "unidade_nome": cls._texto(item.get("unidade_nome") or unidade_nome),
                "produto_id": produto_id,
                "produto_nome": cls._texto(item.get("produto_nome") or item.get("nome")),
                "produto_descricao": cls._texto(item.get("produto_descricao") or item.get("descricao")),
                "imagem_url": cls._texto(item.get("imagem_url")),
                "quantidade": quantidade,
                "observacao": cls._texto(item.get("observacao")),
                "preco_unitario": round(preco_unitario, 2),
                "valor_unitario": round(preco_unitario, 2),
                "preco_unitario_formatado": cls._formatar_moeda(preco_unitario),
                "subtotal": round(subtotal, 2),
                "valor_total": round(subtotal, 2),
                "subtotal_formatado": cls._formatar_moeda(subtotal),
            }

            itens_normalizados.append(item_normalizado)

            if not unidade_id:
                unidade_id = item_normalizado["unidade_id"]

            if not unidade_nome:
                unidade_nome = item_normalizado["unidade_nome"]

        return {
            "unidade_id": unidade_id,
            "unidade_nome": unidade_nome,
            "itens": itens_normalizados,
            "quantidade_itens": len(itens_normalizados),
            "quantidade_total_itens": quantidade_total_itens,
            "subtotal": round(total, 2),
            "total": round(total, 2),
            "total_formatado": cls._formatar_moeda(total),
            "atualizado_em": cls._agora_iso(),
            "atualizado_em_texto": cls._agora_texto(),
        }

    @classmethod
    def adicionar_item_carrinho(cls, carrinho, item_novo):
        carrinho = carrinho or {}
        item_novo = item_novo or {}

        itens = carrinho.get("itens") or []

        unidade_id = cls._texto(item_novo.get("unidade_id"))
        unidade_nome = cls._texto(item_novo.get("unidade_nome"))

        produto_id_novo = cls._texto(item_novo.get("produto_id"))
        observacao_nova = cls._texto(item_novo.get("observacao"))

        encontrou = False

        for item in itens:
            produto_id_atual = cls._texto(item.get("produto_id"))
            observacao_atual = cls._texto(item.get("observacao"))

            if produto_id_atual == produto_id_novo and observacao_atual == observacao_nova:
                item["quantidade"] = int(item.get("quantidade") or 0) + int(item_novo.get("quantidade") or 0)
                encontrou = True
                break

        if not encontrou:
            itens.append(item_novo)

        carrinho["unidade_id"] = unidade_id
        carrinho["unidade_nome"] = unidade_nome
        carrinho["itens"] = itens

        return cls.normalizar_carrinho(carrinho)

    @classmethod
    def atualizar_carrinho_por_formulario(cls, carrinho, form_data):
        carrinho = cls.normalizar_carrinho(carrinho)
        form_data = form_data or {}

        itens_atualizados = []

        for item in carrinho.get("itens") or []:
            produto_id = cls._texto(item.get("produto_id"))

            try:
                quantidade = int(form_data.get(f"quantidade__{produto_id}") or item.get("quantidade") or 1)
            except Exception:
                quantidade = int(item.get("quantidade") or 1)

            if quantidade <= 0:
                quantidade = 1

            observacao = cls._texto(
                form_data.get(f"observacao__{produto_id}")
            )

            item["quantidade"] = quantidade
            item["observacao"] = observacao

            itens_atualizados.append(item)

        carrinho["itens"] = itens_atualizados

        return cls.normalizar_carrinho(carrinho)

    @classmethod
    def remover_item_carrinho(cls, carrinho, produto_id):
        carrinho = cls.normalizar_carrinho(carrinho)
        produto_id = cls._texto(produto_id)

        itens = []

        for item in carrinho.get("itens") or []:
            if cls._texto(item.get("produto_id")) != produto_id:
                itens.append(item)

        carrinho["itens"] = itens

        return cls.normalizar_carrinho(carrinho)

    @classmethod
    def criar_pedido_por_carrinho(cls, cliente_id, carrinho, pagamento_metodo):
        carrinho = cls.normalizar_carrinho(carrinho)
        pagamento_metodo = cls._texto(pagamento_metodo).upper()

        if not carrinho.get("itens"):
            return False, "Seu carrinho está vazio.", None

        unidade_id = cls._texto(carrinho.get("unidade_id"))

        if not unidade_id:
            return False, "Filial inválida no carrinho.", None

        form_pedido = {
            "pagamento_metodo": pagamento_metodo,
        }

        for item in carrinho.get("itens") or []:
            produto_id = cls._texto(item.get("produto_id"))
            quantidade = int(item.get("quantidade") or 0)
            observacao = cls._texto(item.get("observacao"))

            if not produto_id or quantidade <= 0:
                continue

            form_pedido[f"quantidade__{produto_id}"] = str(quantidade)
            form_pedido[f"observacao__{produto_id}"] = observacao

        return cls.criar_pedido(
            cliente_id=cliente_id,
            unidade_id=unidade_id,
            itens_form=form_pedido,
        )

    @classmethod
    def _normalizar_item(cls, item):
        item = item or {}
        snap = item.get("snapshot_produto") or {}

        nome = cls._texto(
            item.get("produto_nome")
            or item.get("nome")
            or snap.get("produto_nome")
            or snap.get("nome")
        )

        descricao = cls._texto(
            item.get("produto_descricao")
            or item.get("descricao")
            or snap.get("produto_descricao")
            or snap.get("descricao")
        )

        return {
            **item,
            "produto_nome": nome or "-",
            "nome": nome or "-",
            "produto_descricao": descricao or "-",
            "descricao": descricao or "-",
            "snapshot_produto": {
                **snap,
                "nome": nome or "-",
                "produto_nome": nome or "-",
                "descricao": descricao or "-",
                "produto_descricao": descricao or "-",
                "imagem_url": cls._texto(snap.get("imagem_url") or item.get("imagem_url")),
            },
            "quantidade": int(item.get("quantidade") or 0),
            "preco_unitario_formatado": cls._texto(item.get("preco_unitario_formatado")) or cls._formatar_moeda(item.get("preco_unitario") or item.get("valor_unitario")),
            "subtotal_formatado": cls._texto(item.get("subtotal_formatado")) or cls._formatar_moeda(item.get("subtotal") or item.get("valor_total")),
        }

    @classmethod
    def _normalizar_pedido(cls, doc_id, data):
        data = data or {}

        status = cls._normalizar_status(data.get("status"))
        valor_total = float(data.get("valor_total") or data.get("total") or 0.0)
        itens = [cls._normalizar_item(item) for item in (data.get("itens") or []) if isinstance(item, dict)]
        historico = data.get("historico") or []

        historico.sort(key=lambda x: cls._texto(x.get("criado_em")), reverse=True)
        historico_cliente = cls._normalizar_historico_cliente(historico)

        origem = cls._texto(data.get("origem") or data.get("tipo") or data.get("canal") or cls.ORIGEM_CLIENTE_WEB)

        pagamento_status = cls._normalizar_pagamento(
            data.get("pagamento_status")
            or data.get("situacao_pagamento")
            or cls.PAGAMENTO_AGUARDANDO
        )

        status_cliente = cls._status_cliente(status, pagamento_status)

        return {
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
            "pode_cancelar": cls._pode_cancelar(status, pagamento_status),

            "status_cliente_codigo": status_cliente["codigo"],
            "status_cliente_descricao": status_cliente["descricao"],
            "status_cliente_mensagem": status_cliente["mensagem"],
            "status_cliente_etapa": status_cliente["etapa"],

            "origem": origem,
            "tipo": cls._texto(data.get("tipo") or origem),
            "canal": cls._texto(data.get("canal") or origem),

            "situacao_pagamento": cls._texto(data.get("situacao_pagamento") or cls.PAGAMENTO_PENDENTE).upper(),

            "pagamento_status": pagamento_status,
            "pagamento_status_descricao": (
                cls._texto(data.get("pagamento_status_descricao"))
                or cls._descricao_pagamento(pagamento_status)
            ),

            "forma_pagamento": cls._texto(data.get("forma_pagamento") or data.get("pagamento_metodo")),
            "pagamento_metodo": cls._texto(data.get("pagamento_metodo") or data.get("forma_pagamento")),
            "pagamento_metodo_descricao": (
                cls._texto(data.get("pagamento_metodo_descricao"))
                or cls._texto(data.get("pagamento_metodo"))
                or cls._texto(data.get("forma_pagamento"))
            ),

            "pagamento_valor": float(data.get("pagamento_valor") or valor_total),
            "pagamento_valor_formatado": (
                cls._texto(data.get("pagamento_valor_formatado"))
                or cls._formatar_moeda(data.get("pagamento_valor") or valor_total)
            ),
            "pagamento_transacao_id": cls._texto(data.get("pagamento_transacao_id")),
            "pago_em": cls._texto(data.get("pago_em")),

            "itens": itens,
            "historico": historico,

            "quantidade_itens": int(data.get("quantidade_itens") or len(itens)),
            "quantidade_total_itens": int(data.get("quantidade_total_itens") or sum(item.get("quantidade", 0) for item in itens)),

            "subtotal": float(data.get("subtotal") or valor_total),
            "total": float(data.get("total") or valor_total),

            "valor_produtos": float(data.get("valor_produtos") or data.get("subtotal") or valor_total),
            "valor_desconto": float(data.get("valor_desconto") or 0),
            "valor_entrega": float(data.get("valor_entrega") or 0),
            "valor_total": valor_total,
            "valor_total_formatado": (
                cls._texto(data.get("valor_total_formatado"))
                or cls._formatar_moeda(valor_total)
            ),

            "criado_em": cls._texto(data.get("criado_em")),
            "criado_em_texto": cls._texto(data.get("criado_em_texto")),
            "criado_em_ord": cls._texto(data.get("criado_em_ord")),
            "atualizado_em": cls._texto(data.get("atualizado_em")),
            "atualizado_em_texto": cls._texto(data.get("atualizado_em_texto")),

            "cancelado_em": cls._texto(data.get("cancelado_em")),
            "motivo_cancelamento": cls._texto(data.get("motivo_cancelamento")),
        }

    @classmethod
    def listar_pedidos_do_cliente(cls, cliente_id):
        cliente_id = cls._texto(cliente_id)

        if not cliente_id:
            return []

        docs = cls._collection(cls.COLLECTION_PEDIDOS).where("cliente_id", "==", cliente_id).stream()

        pedidos = []

        for doc in docs:
            pedidos.append(cls._normalizar_pedido(doc.id, doc.to_dict()))

        pedidos.sort(
            key=lambda x: x.get("criado_em_ord") or x.get("criado_em", ""),
            reverse=True
        )

        return pedidos

    @classmethod
    def buscar_ultimo_pedido_do_cliente(cls, cliente_id):
        pedidos = cls.listar_pedidos_do_cliente(cliente_id)

        if not pedidos:
            return None

        return pedidos[0]

    @classmethod
    def buscar_pedido_do_cliente(cls, cliente_id, pedido_id):
        cliente_id = cls._texto(cliente_id)
        pedido_id = cls._texto(pedido_id)

        if not cliente_id or not pedido_id:
            return None

        doc = cls._collection(cls.COLLECTION_PEDIDOS).document(pedido_id).get()

        if not doc.exists:
            return None

        pedido = cls._normalizar_pedido(doc.id, doc.to_dict())

        if pedido["cliente_id"] != cliente_id:
            return None

        return pedido

    @classmethod
    def cancelar_pedido_do_cliente(cls, cliente_id, pedido_id):
        pedido = cls.buscar_pedido_do_cliente(cliente_id, pedido_id)

        if not pedido:
            return False, "Pedido não encontrado.", None

        if not pedido["pode_cancelar"]:
            return False, "Este pedido não pode mais ser cancelado.", None

        agora = cls._agora_iso()
        agora_texto = cls._agora_texto()

        historico = list(pedido.get("historico") or [])

        historico.append(
            cls._novo_evento_historico(
                tipo="CANCELAMENTO",
                descricao="Pedido cancelado pelo cliente",
                usuario_tipo="CLIENTE",
                usuario_nome=pedido.get("cliente_nome") or pedido.get("cliente_email"),
                status_anterior=pedido.get("status"),
                status_novo=cls.STATUS_CANCELADO,
                motivo="Cancelado pelo cliente",
            )
        )

        cls._collection(cls.COLLECTION_PEDIDOS).document(pedido_id).update({
            "status": cls.STATUS_CANCELADO,
            "origem": cls.ORIGEM_CLIENTE_WEB,
            "tipo": cls.ORIGEM_CLIENTE_WEB,
            "canal": cls.ORIGEM_CLIENTE_WEB,
            "atualizado_em": agora,
            "atualizado_em_texto": agora_texto,
            "cancelado_em": agora,
            "motivo_cancelamento": "Cancelado pelo cliente",
            "historico": historico,
        })

        pedido_atualizado = cls.buscar_pedido_do_cliente(cliente_id, pedido_id)

        return True, "Pedido cancelado com sucesso.", pedido_atualizado