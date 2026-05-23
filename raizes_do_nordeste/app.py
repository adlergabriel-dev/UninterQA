from datetime import datetime

from flask import Flask

from bp import register_blueprints
from config import SECRET_KEY, FIREBASE_API_KEY


def formatar_data_br(valor):
    if not valor:
        return "-"

    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M")

    texto = str(valor).strip()

    if not texto:
        return "-"

    try:
        # Remove microssegundos quando vier assim:
        # 2026-05-23T15:19:17.927745
        # 2026-05-23 15:19:17.927745
        if "." in texto and "+" not in texto:
            texto = texto.split(".")[0]

        # Trata data ISO com Z
        if texto.endswith("Z"):
            texto = texto.replace("Z", "+00:00")

        # Trata ISO: 2026-05-23T15:19:17
        if "T" in texto:
            dt = datetime.fromisoformat(texto)
            return dt.strftime("%d/%m/%Y %H:%M")

        formatos = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
        ]

        for formato in formatos:
            try:
                dt = datetime.strptime(texto, formato)

                if formato in ["%Y-%m-%d", "%d/%m/%Y"]:
                    return dt.strftime("%d/%m/%Y")

                return dt.strftime("%d/%m/%Y %H:%M")

            except Exception:
                pass

        dt = datetime.fromisoformat(texto)
        return dt.strftime("%d/%m/%Y %H:%M")

    except Exception:
        return texto


def create_app():
    app = Flask(__name__)
    app.secret_key = SECRET_KEY
    app.config["FIREBASE_API_KEY"] = FIREBASE_API_KEY

    app.jinja_env.filters["datetime_br"] = formatar_data_br
    app.jinja_env.filters["data_br"] = formatar_data_br

    register_blueprints(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)