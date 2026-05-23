from datetime import datetime
from services.firebase_service import FirebaseService


class UnidadeService:
    COLLECTION = "unidades"

    @classmethod
    def listar(cls):
        docs = FirebaseService.get_collection(cls.COLLECTION).stream()
        resultado = []

        for doc in docs:
            item = doc.to_dict()
            item["id"] = doc.id
            resultado.append(item)

        resultado.sort(key=lambda x: x.get("nome", ""))
        return resultado

    @classmethod
    def buscar_por_id(cls, unidade_id: str):
        doc_ref = FirebaseService.get_collection(cls.COLLECTION).document(unidade_id)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict()
        data["id"] = doc.id
        return data

    @classmethod
    def criar(cls, dados: dict):
        agora = datetime.utcnow().isoformat()

        payload = {
            "nome": dados.get("nome", "").strip(),
            "codigo": dados.get("codigo", "").strip().upper(),
            "telefone": dados.get("telefone", "").strip(),
            "email": dados.get("email", "").strip(),
            "endereco": dados.get("endereco", "").strip(),
            "cidade": dados.get("cidade", "").strip(),
            "estado": dados.get("estado", "").strip().upper(),
            "cep": dados.get("cep", "").strip(),
            "ativo": True,
            "criado_em": agora,
            "atualizado_em": agora,
        }

        doc_ref = FirebaseService.get_collection(cls.COLLECTION).document()
        doc_ref.set(payload)
        return doc_ref.id

    @classmethod
    def atualizar(cls, unidade_id: str, dados: dict):
        payload = {
            "nome": dados.get("nome", "").strip(),
            "codigo": dados.get("codigo", "").strip().upper(),
            "telefone": dados.get("telefone", "").strip(),
            "email": dados.get("email", "").strip(),
            "endereco": dados.get("endereco", "").strip(),
            "cidade": dados.get("cidade", "").strip(),
            "estado": dados.get("estado", "").strip().upper(),
            "cep": dados.get("cep", "").strip(),
            "atualizado_em": datetime.utcnow().isoformat(),
        }

        FirebaseService.get_collection(cls.COLLECTION).document(unidade_id).update(payload)

    @classmethod
    def alterar_status(cls, unidade_id: str, ativo: bool):
        FirebaseService.get_collection(cls.COLLECTION).document(unidade_id).update({
            "ativo": ativo,
            "atualizado_em": datetime.utcnow().isoformat(),
        })