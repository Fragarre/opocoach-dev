from pathlib import Path

import streamlit as st

from procesos.generar_simulacro import (
    generar_simulacro_convocatoria,
)


ROOT = Path(__file__).resolve().parent

RUTA_SIMULACROS = ROOT / "simulacros"


st.set_page_config(
    page_title="OpoCoach",
    page_icon="📝",
    layout="centered",
)


st.title("OpoCoach")

st.subheader(
    "Generador de simulacros"
)


convocatoria = st.selectbox(
    "Convocatoria",
    options=[
        "C1-01_58_26",
    ],
)


if "simulacro_generado" not in st.session_state:

    st.session_state.simulacro_generado = None


if st.button(
    "Generar simulacro",
    type="primary",
):

    with st.spinner(
        "Generando simulacro..."
    ):

        generado = generar_simulacro_convocatoria(
            convocatoria
        )

    resultado = generado["resultado"]

    if not resultado["completo"]:

        st.session_state.simulacro_generado = None

        st.error(
            "No se ha podido completar el simulacro."
        )

        for faltante in resultado["faltantes"]:

            st.write(
                f"{faltante['tipo_pregunta']}: "
                f"faltan {faltante['faltan']}"
            )

    else:

        ruta_pdf_preguntas = generado[
            "ruta_pdf_preguntas"
        ]

        ruta_pdf_soluciones = generado[
            "ruta_pdf_soluciones"
        ]

        st.session_state.simulacro_generado = {
            "generado": generado,
            "pdf_preguntas": (
                ruta_pdf_preguntas.read_bytes()
            ),
            "pdf_soluciones": (
                ruta_pdf_soluciones.read_bytes()
            ),
        }


datos_sesion = (
    st.session_state.simulacro_generado
)


if datos_sesion is not None:

    generado = datos_sesion["generado"]

    simulacro = generado["simulacro"]

    resultado = generado["resultado"]

    identificador = generado[
        "ruta_json"
    ].stem

    st.success(
        f"Simulacro generado: {identificador}"
    )

    st.caption(
        f"Convocatoria: "
        f"{generado['convocatoria']['codigo_cfg']} "
        f"· Total: {resultado['total']} preguntas"
    )

    resumen = resultado[
        "resumen_bloques"
    ]

    st.write(
        (
            f"**Teoría:** "
            f"{resumen['ESPECIAL_TEORIA']['obtenidas']}"
            f"/{resumen['ESPECIAL_TEORIA']['objetivo']} · "
            f"**Práctica:** "
            f"{resumen['ESPECIAL_PRACTICA']['obtenidas']}"
            f"/{resumen['ESPECIAL_PRACTICA']['objetivo']} · "
            f"**Informática:** "
            f"{resumen['ESPECIAL_INFORMATICA']['obtenidas']}"
            f"/{resumen['ESPECIAL_INFORMATICA']['objetivo']} · "
            f"**General:** "
            f"{resumen['GENERAL']['obtenidas']}"
            f"/{resumen['GENERAL']['objetivo']}"
        )
    )
    st.divider()

    st.download_button(
        label="Descargar simulacro",
        data=datos_sesion[
            "pdf_preguntas"
        ],
        file_name=generado[
            "ruta_pdf_preguntas"
        ].name,
        mime="application/pdf",
        type="primary",
        use_container_width=True,
        on_click="ignore",
    )

    st.download_button(
        label="Descargar solucionario",
        data=datos_sesion[
            "pdf_soluciones"
        ],
        file_name=generado[
            "ruta_pdf_soluciones"
        ].name,
        mime="application/pdf",
        use_container_width=True,
        on_click="ignore",
    )

    st.divider()

    with st.expander(
        "Corrección del simulacro",
        expanded=False,
    ):

        st.write(
            "Introduce tus respuestas para corregir este simulacro."
        )

        for numero in range(
            1,
            resultado["total"] + 1,
        ):

            st.radio(
                f"Pregunta {numero}",
                options=[
                    "En blanco",
                    "A",
                    "B",
                    "C",
                    "D",
                ],
                horizontal=True,
                key=(
                    f"respuesta_"
                    f"{identificador}_"
                    f"{numero}"
                ),
            )

        st.divider()

        if st.button(
            "Corregir respuestas",
            type="primary",
            key=f"corregir_{identificador}",
            use_container_width=True,
        ):

            aciertos = 0
            errores = 0
            blancos = 0

            for pregunta in simulacro.preguntas:

                respuesta_usuario = st.session_state[
                    (
                        f"respuesta_"
                        f"{identificador}_"
                        f"{pregunta.numero}"
                    )
                ]

                if respuesta_usuario == "En blanco":

                    blancos += 1

                elif (
                    respuesta_usuario
                    == pregunta.respuesta_correcta
                ):

                    aciertos += 1

                else:

                    errores += 1

            st.session_state[
                f"resultado_correccion_{identificador}"
            ] = {
                "aciertos": aciertos,
                "errores": errores,
                "blancos": blancos,
            }
        clave_resultado = (
        f"resultado_correccion_{identificador}"
    )

    if clave_resultado in st.session_state:

        resultado_correccion = st.session_state[
            clave_resultado
        ]

        st.success(
            (
                f"Aciertos: "
                f"{resultado_correccion['aciertos']} · "
                f"Errores: "
                f"{resultado_correccion['errores']} · "
                f"En blanco: "
                f"{resultado_correccion['blancos']}"
            )
        )