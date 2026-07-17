from __future__ import annotations

import sys
from pathlib import Path

try:
    import img2pdf
except ImportError:
    print(
        "Falta img2pdf. Instálalo con: py -m pip install img2pdf",
        file=sys.stderr,
    )
    raise SystemExit(2)


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Uso: crear_pdf.py CARPETA_CAPTURAS ARCHIVO_SALIDA.pdf",
            file=sys.stderr,
        )
        return 1

    carpeta = Path(sys.argv[1])
    salida = Path(sys.argv[2])

    if not carpeta.is_dir():
        print(f"No existe la carpeta: {carpeta}", file=sys.stderr)
        return 2

    imagenes = sorted(
        carpeta.glob("*.jpg"),
        key=lambda ruta: int(ruta.stem)
        if ruta.stem.isdigit()
        else ruta.name,
    )

    if not imagenes:
        print("No hay imágenes JPG.", file=sys.stderr)
        return 3

    salida.parent.mkdir(parents=True, exist_ok=True)

    rutas = [str(imagen) for imagen in imagenes]

    with salida.open("wb") as archivo:
        archivo.write(img2pdf.convert(rutas))

    print(f"PDF creado: {salida}")
    print(f"Imágenes incluidas: {len(imagenes)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())