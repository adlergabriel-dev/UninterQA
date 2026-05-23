from datetime import datetime
from services.firebase_service import FirebaseService
from services.unidade_service import UnidadeService
from services.produto_service import ProdutoService


class CardapioService:
    COLECAO = "cardapio_unidade"

    @classmethod
    def listar(cls):
        docs = FirebaseService.get_collection(cls.COLECAO).stream()
        resultado = []

        for doc in docs:
            item = doc.to_dict() or {}
            item["id"] = doc.id
            resultado.append(item)

        resultado.sort(
            key=lambda x: (
                (x.get("nome_unidade", "") or "").lower(),
                x.get("ordem_exibicao", 9999),
                (x.get("nome_produto", "") or "").lower(),
            )
        )
        return resultado

    @classmethod
    def buscar_por_id(cls, cardapio_id: str):
        doc_ref = FirebaseService.get_collection(cls.COLECAO).document(cardapio_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    @classmethod
    def existe_vinculo(cls, unidade_id: str, produto_id: str, ignorar_id: str = None):
        docs = (
            FirebaseService.get_collection(cls.COLECAO)
            .where("unidade_id", "==", unidade_id)
            .where("produto_id", "==", produto_id)
            .stream()
        )

        for doc in docs:
            if ignorar_id and doc.id == ignorar_id:
                continue
            return True

        return False

    @classmethod
    def criar(cls, dados: dict):
        unidade_id = (dados.get("unidade_id") or "").strip()
        produto_id = (dados.get("produto_id") or "").strip()

        unidade = UnidadeService.buscar_por_id(unidade_id)
        produto = ProdutoService.buscar_por_id(produto_id)

        if not unidade:
            raise ValueError("Unidade não encontrada.")

        if not produto:
            raise ValueError("Produto não encontrado.")

        if cls.existe_vinculo(unidade_id, produto_id):
            raise ValueError("Este produto já está vinculado a esta unidade.")

        agora = datetime.utcnow().isoformat()

        payload = {
            "unidade_id": unidade_id,
            "produto_id": produto_id,
            "nome_unidade": unidade.get("nome", ""),
            "nome_produto": produto.get("nome", ""),
            "imagem_url": produto.get("imagem_url", ""),
            "preco_venda": float(str(dados.get("preco_venda", "0")).replace(",", ".")),
            "disponivel": str(dados.get("disponivel", "false")).lower() in ["true", "1", "on", "sim"],
            "destaque": str(dados.get("destaque", "false")).lower() in ["true", "1", "on", "sim"],
            "ordem_exibicao": int(dados.get("ordem_exibicao", 0) or 0),
            "ativo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        }

        doc_ref = FirebaseService.get_collection(cls.COLECAO).document()
        doc_ref.set(payload)
        return doc_ref.id

    @classmethod
    def atualizar(cls, cardapio_id: str, dados: dict):
        unidade_id = (dados.get("unidade_id") or "").strip()
        produto_id = (dados.get("produto_id") or "").strip()

        unidade = UnidadeService.buscar_por_id(unidade_id)
        produto = ProdutoService.buscar_por_id(produto_id)

        if not unidade:
            raise ValueError("Unidade não encontrada.")

        if not produto:
            raise ValueError("Produto não encontrado.")

        if cls.existe_vinculo(unidade_id, produto_id, ignorar_id=cardapio_id):
            raise ValueError("Este produto já está vinculado a esta unidade.")

        payload = {
            "unidade_id": unidade_id,
            "produto_id": produto_id,
            "nome_unidade": unidade.get("nome", ""),
            "nome_produto": produto.get("nome", ""),
            "imagem_url": produto.get("imagem_url", ""),
            "preco_venda": float(str(dados.get("preco_venda", "0")).replace(",", ".")),
            "disponivel": str(dados.get("disponivel", "false")).lower() in ["true", "1", "on", "sim"],
            "destaque": str(dados.get("destaque", "false")).lower() in ["true", "1", "on", "sim"],
            "ordem_exibicao": int(dados.get("ordem_exibicao", 0) or 0),
            "atualizado_em": datetime.utcnow().isoformat(),
        }

        FirebaseService.get_collection(cls.COLECAO).document(cardapio_id).update(payload)

    @classmethod
    def alterar_status(cls, cardapio_id: str, ativo: bool):
        FirebaseService.get_collection(cls.COLECAO).document(cardapio_id).update({
            "ativo": ativo,
            "atualizado_em": datetime.utcnow().isoformat(),
        })