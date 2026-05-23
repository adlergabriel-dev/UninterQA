from services.firebase_service import FirebaseService


class AuthService:
    COLECAO = "usuarios"

    @classmethod
    def buscar_por_uid(cls, uid: str):
        if not uid:
            return None

        doc_ref = FirebaseService.get_collection(cls.COLECAO).document(uid)
        doc = doc_ref.get()

        if not doc.exists:
            return None

        data = doc.to_dict() or {}
        data["id"] = doc.id
        return data

    @classmethod
    def buscar_por_email(cls, email: str):
        email = (email or "").strip().lower()
        if not email:
            return None

        docs = (
            FirebaseService.get_collection(cls.COLECAO)
            .where("email", "==", email)
            .stream()
        )

        for doc in docs:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            return data

        return None