import hashlib


def calcular_huella(
    enunciado,
    opciones,
):

    texto = enunciado.strip()

    for letra in ("A", "B", "C", "D"):

        texto += "\n"
        texto += opciones[letra].strip()

    return hashlib.sha256(
        texto.encode("utf-8")
    ).hexdigest()