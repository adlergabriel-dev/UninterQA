from datetime import datetime
from services.firebase_service import FirebaseService


class ClienteService:
    COLECAO = "clientes"

    @classmethod
    def listar(cls):
        docs = FirebaseService.get_collection(cls.COLECAO).stream()
        resultado = []

        for doc in docs:
            item = doc.to_dict()
            item["id"] = doc.id
            resultado.append(item)

        resultado.sort(key=lambda x: x.get("nome", "").lower())
        return resultado

    @classmethod
    def buscar_por_id(cls, cliente_id: str):
        doc_ref = FirebaseService.get_collection(cls.COLECAO).document(cliente_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        data["id"] = doc.id
        return data

    @classmethod
    def buscar_por_telefone(cls, telefone: str):
        docs = (
            FirebaseService.get_collection(cls.COLECAO)
            .where("telefone", "==", telefone.strip())
            .stream()
        )

        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            return data

        return None

    @classmethod
    def criar(cls, dados: dict):
        agora = datetime.utcnow().isoformat()

        payload = {
            "nome": dados.get("nome", "").strip(),
            "telefone": dados.get("telefone", "").strip(),
            "email": dados.get("email", "").strip(),
            "cpf": dados.get("cpf", "").strip(),
            "ativo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        }

        doc_ref = FirebaseService.get_collection(cls.COLECAO).document()
        doc_ref.set(payload)
        return doc_ref.id

    @classmethod
    def atualizar(cls, cliente_id: str, dados: dict):
        payload = {
            "nome": dados.get("nome", "").strip(),
            "telefone": dados.get("telefone", "").strip(),
            "email": dados.get("email", "").strip(),
            "cpf": dados.get("cpf", "").strip(),
            "atualizado_em": datetime.utcnow().isoformat(),
        }

        FirebaseService.get_collection(cls.COLECAO).document(cliente_id).update(payload)

    @classmethod
    def alterar_status(cls, cliente_id: str, ativo: bool):
        FirebaseService.get_collection(cls.COLECAO).document(cliente_id).update({
            "ativo": ativo,
            "atualizado_em": datetime.utcnow().isoformat(),
        })