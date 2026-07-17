from pathlib import Path


for ruta in Path(".").rglob("*.py"):

    if ".venv" in ruta.parts:
        continue

    try:
        ruta.read_text(encoding="utf-8")

    except UnicodeDecodeError as error:
        print(
            f"NO UTF-8: {ruta} "
            f"| posición: {error.start} "
            f"| byte: {error.object[error.start:error.start + 1].hex()}"
        )
        