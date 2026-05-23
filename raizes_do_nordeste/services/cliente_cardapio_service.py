from services.firebase_service import FirebaseService


class ClienteCardapioService:
    COLLECTION_CLIENTES = "clientes"
    COLLECTION_UNIDADES = "unidades"
    COLLECTION_PRODUTOS = "produtos"
    COLLECTION_CARDAPIO = "cardapio_unidade"

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
            ativo = cls._bool(data.get("ativo"), True)
            if not ativo:
                continue

            unidades.append({
                "id": doc.id,
                "nome": cls._texto(data.get("nome")),
                "ativo": ativo,
            })

        unidades.sort(key=lambda x: cls._texto_lower(x.get("nome")))
        return unidades

    @classmethod
    def _mapear_produtos_ativos(cls):
        docs = cls._collection(cls.COLLECTION_PRODUTOS).stream()
        produtos = {}

        for doc in docs:
            data = doc.to_dict() or {}
            ativo = cls._bool(data.get("ativo"), True)
            if not ativo:
                continue

            produtos[doc.id] = {
                "id": doc.id,
                "nome": cls._texto(data.get("nome")),
                "descricao": cls._texto(data.get("descricao")),
                "imagem_url": cls._texto(data.get("imagem_url") or data.get("imagem")),
                "ativo": ativo,
            }

        return produtos

    @classmethod
    def _mapear_unidades_ativas(cls):
        docs = cls._collection(cls.COLLECTION_UNIDADES).stream()
        unidades = {}

        for doc in docs:
            data = doc.to_dict() or {}
            ativo = cls._bool(data.get("ativo"), True)
            if not ativo:
                continue

            unidades[doc.id] = {
                "id": doc.id,
                "nome": cls._texto(data.get("nome")),
                "ativo": ativo,
            }

        return unidades

    @classmethod
    def listar_cardapio_publico(cls, unidade_id="", termo=""):
        unidade_id = cls._texto(unidade_id)
        termo = cls._texto_lower(termo)

        produtos_map = cls._mapear_produtos_ativos()
        unidades_map = cls._mapear_unidades_ativas()

        docs = cls._collection(cls.COLLECTION_CARDAPIO).stream()
        itens = []

        for doc in docs:
            data = doc.to_dict() or {}

            ativo = cls._bool(data.get("ativo"), True)
            if not ativo:
                continue

            item_unidade_id = cls._texto(
                data.get("unidade_id")
                or data.get("id_unidade")
                or data.get("unidadeId")
            )
            item_produto_id = cls._texto(
                data.get("produto_id")
                or data.get("id_produto")
                or data.get("produtoId")
            )

            if not item_unidade_id or not item_produto_id:
                continue

            unidade = unidades_map.get(item_unidade_id)
            produto = produtos_map.get(item_produto_id)

            nome_unidade = cls._texto((unidade or {}).get("nome") or data.get("nome_unidade"))
            nome_produto = cls._texto((produto or {}).get("nome") or data.get("nome_produto"))
            descricao_produto = cls._texto((produto or {}).get("descricao") or data.get("descricao_produto"))
            imagem_url = cls._texto((produto or {}).get("imagem_url") or data.get("imagem_url"))

            if not nome_unidade or not nome_produto:
                continue

            if unidade_id and item_unidade_id != unidade_id:
                continue

            texto_busca = " ".join([
                nome_produto.lower(),
                descricao_produto.lower(),
                nome_unidade.lower(),
            ])

            if termo and termo not in texto_busca:
                continue

            preco = data.get("preco")
            if preco in [None, ""]:
                preco = data.get("preco_venda")

            try:
                preco = float(preco) if preco not in [None, ""] else 0.0
            except Exception:
                preco = 0.0

            itens.append({
                "id": doc.id,
                "unidade_id": item_unidade_id,
                "unidade_nome": nome_unidade,
                "produto_id": item_produto_id,
                "produto_nome": nome_produto,
                "produto_descricao": descricao_produto,
                "imagem_url": imagem_url,
                "preco": preco,
                "preco_formatado": f"R$ {preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            })

        itens.sort(
            key=lambda x: (
                cls._texto_lower(x.get("unidade_nome")),
                cls._texto_lower(x.get("produto_nome")),
            )
        )
        return itens