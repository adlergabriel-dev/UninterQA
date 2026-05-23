import firebase_admin
from firebase_admin import credentials, firestore
from config import FIREBASE_CREDENTIALS_FILE


class FirebaseService:
    _db = None

    @classmethod
    def inicializar(cls):
        """
        Inicializa o Firebase apenas uma vez e retorna o cliente Firestore.
        """
        if cls._db is None:
            if not firebase_admin._apps:
                cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
                firebase_admin.initialize_app(cred)

            cls._db = firestore.client()

        return cls._db

    @classmethod
    def get_db(cls):
        """
        Retorna a instância do Firestore.
        """
        return cls.inicializar()

    @classmethod
    def get_collection(cls, nome_colecao):
        """
        Retorna uma coleção do Firestore.
        """
        db = cls.get_db()
        return db.collection(nome_colecao)

    @classmethod
    def listar_documentos(cls, nome_colecao):
        """
        Lista todos os documentos de uma coleção.
        Inclui o ID do documento no campo 'id'.
        """
        collection = cls.get_collection(nome_colecao)
        docs = collection.stream()

        resultado = []

        for doc in docs:
            dados = doc.to_dict() or {}
            dados["id"] = doc.id
            resultado.append(dados)

        return resultado

    @classmethod
    def buscar_documento_por_id(cls, nome_colecao, documento_id):
        """
        Busca um documento específico pelo ID.
        """
        if not documento_id:
            return None

        collection = cls.get_collection(nome_colecao)
        doc = collection.document(str(documento_id)).get()

        if not doc.exists:
            return None

        dados = doc.to_dict() or {}
        dados["id"] = doc.id

        return dados

    @classmethod
    def criar_documento(cls, nome_colecao, dados):
        """
        Cria um documento novo com ID automático.
        Retorna o ID criado.
        """
        collection = cls.get_collection(nome_colecao)
        ref = collection.document()
        ref.set(dados)

        return ref.id

    @classmethod
    def criar_documento_com_id(cls, nome_colecao, documento_id, dados):
        """
        Cria ou sobrescreve um documento usando um ID específico.
        """
        if not documento_id:
            raise ValueError("documento_id não informado.")

        collection = cls.get_collection(nome_colecao)
        collection.document(str(documento_id)).set(dados)

        return str(documento_id)

    @classmethod
    def atualizar_documento(cls, nome_colecao, documento_id, dados):
        """
        Atualiza um documento existente.
        """
        if not documento_id:
            raise ValueError("documento_id não informado.")

        collection = cls.get_collection(nome_colecao)
        collection.document(str(documento_id)).update(dados)

        return True

    @classmethod
    def deletar_documento(cls, nome_colecao, documento_id):
        """
        Remove um documento do Firestore.
        """
        if not documento_id:
            raise ValueError("documento_id não informado.")

        collection = cls.get_collection(nome_colecao)
        collection.document(str(documento_id)).delete()

        return True

    @classmethod
    def filtrar_documentos(cls, nome_colecao, campo, operador, valor):
        """
        Filtra documentos de uma coleção.
        Exemplo:
        FirebaseService.filtrar_documentos("pedidos", "origem", "==", "TOTEM")
        """
        collection = cls.get_collection(nome_colecao)
        docs = collection.where(campo, operador, valor).stream()

        resultado = []

        for doc in docs:
            dados = doc.to_dict() or {}
            dados["id"] = doc.id
            resultado.append(dados)

        return resultado