#Requires AutoHotkey v2.0
#SingleInstance Force

; ============================================================
; CONFIGURACIÓN
; ============================================================

; Cambiar si usas otro navegador:
navegador := "chrome.exe"

; Microsoft Edge:
; navegador := "msedge.exe"

; Firefox:
; navegador := "firefox.exe"

carpetaCapturas := A_ScriptDir "\capturas_test"
scriptGuardar   := A_ScriptDir "\guardar_portapapeles.ps1"
scriptPDF       := A_ScriptDir "\crear_pdf.py"

; En la mayoría de instalaciones de Python funciona "py".
comandoPython := "py"

capturando := false


; ============================================================
; CREAR CARPETA DE CAPTURAS
; ============================================================

if !DirExist(carpetaCapturas)
    DirCreate(carpetaCapturas)


; ============================================================
; L -> ACTIVAR LA APLICACIÓN DEL TEST
; ============================================================

º::
{
    global navegador

    KeyWait("l")

    ventanaTest := "ahk_exe " navegador

    if !WinExist(ventanaTest)
    {
        MsgBox("No encuentro el navegador configurado: " navegador)
        return
    }

    WinActivate(ventanaTest)

    if !WinWaitActive(ventanaTest, , 2)
    {
        MsgBox("No se ha podido activar el navegador.")
        return
    }
}


; ============================================================
; A -> SELECCIONAR ÁREA Y GUARDARLA COMO JPG
; ============================================================

w::
{
    global navegador
    global carpetaCapturas
    global scriptGuardar
    global capturando

    if capturando
        return

    capturando := true
    KeyWait("a")

    try
    {
        ventanaTest := "ahk_exe " navegador

        if !WinExist(ventanaTest)
        {
            MsgBox("No encuentro el navegador.")
            return
        }

        if !FileExist(scriptGuardar)
        {
            MsgBox(
                "No encuentro el archivo:`n`n"
                scriptGuardar
            )
            return
        }

        WinActivate(ventanaTest)

        if !WinWaitActive(ventanaTest, , 2)
        {
            MsgBox("No se ha podido activar el navegador.")
            return
        }

        ; Vaciar el portapapeles para detectar la nueva captura.
        A_Clipboard := ""

        ; Abrir el selector de área de Windows.
        Send("#+s")

        ; Aquí seleccionas manualmente la pregunta.
        if !ClipWait(60, 1)
        {
            MsgBox("No se ha detectado ninguna captura.")
            return
        }

        numero := ObtenerSiguienteNumero(carpetaCapturas)
        nombre := Format("{:04}.jpg", numero)
        archivoSalida := carpetaCapturas "\" nombre

        comando :=
            'powershell.exe -NoProfile -ExecutionPolicy Bypass '
            . '-File "' scriptGuardar '" '
            . '-Salida "' archivoSalida '"'

        codigoSalida := RunWait(comando, , "Hide")

        if codigoSalida != 0 || !FileExist(archivoSalida)
        {
            MsgBox(
                "No se ha podido guardar la captura.`n`n"
                "Código de error: " codigoSalida
            )
            return
        }

        ; Volver inmediatamente al test.
        WinActivate(ventanaTest)
        WinWaitActive(ventanaTest, , 2)

        ToolTip("Guardada: " nombre)
        SetTimer(() => ToolTip(), -700)
    }
    finally
    {
        capturando := false
    }
}


; ============================================================
; P -> CREAR EL PDF SIN CERRAR EL SCRIPT
; ============================================================

<::
{
    global carpetaCapturas
    global scriptPDF
    global comandoPython

    KeyWait("p")
    CrearPDF(carpetaCapturas, scriptPDF, comandoPython)
}


; ============================================================
; Q -> CREAR EL PDF Y CERRAR EL SCRIPT
; ============================================================

>::
{
    global carpetaCapturas
    global scriptPDF
    global comandoPython

    KeyWait("q")

    if CrearPDF(carpetaCapturas, scriptPDF, comandoPython)
        ExitApp()
}


; ============================================================
; CTRL + ESC -> CERRAR SIN CREAR PDF
; ============================================================

^Esc::
{
    ExitApp()
}


; ============================================================
; OBTENER SIGUIENTE NÚMERO DISPONIBLE
; ============================================================

ObtenerSiguienteNumero(carpeta)
{
    maximo := 0

    Loop Files carpeta "\*.jpg"
    {
        SplitPath(A_LoopFileName, , , , &nombreSinExtension)

        if IsInteger(nombreSinExtension)
        {
            numero := Integer(nombreSinExtension)

            if numero > maximo
                maximo := numero
        }
    }

    return maximo + 1
}


; ============================================================
; CREAR PDF
; ============================================================

CrearPDF(carpeta, scriptPDF, comandoPython)
{
    if !FileExist(scriptPDF)
    {
        MsgBox(
            "No encuentro el archivo:`n`n"
            scriptPDF
        )
        return false
    }

    cantidad := 0

    Loop Files carpeta "\*.jpg"
        cantidad++

    if cantidad = 0
    {
        MsgBox("No hay capturas para convertir en PDF.")
        return false
    }

    marcaTiempo := FormatTime(, "yyyyMMdd_HHmmss")
    archivoPDF := A_ScriptDir "\TEST_" marcaTiempo ".pdf"

    comando :=
        comandoPython
        . ' "' scriptPDF '" '
        . '"' carpeta '" '
        . '"' archivoPDF '"'

    ToolTip("Creando PDF con " cantidad " capturas...")

    codigoSalida := RunWait(comando, , "Hide")

    ToolTip()

    if codigoSalida != 0 || !FileExist(archivoPDF)
    {
        MsgBox(
            "No se ha podido crear el PDF.`n`n"
            "Comprueba que Python e img2pdf están instalados."
        )
        return false
    }

    MsgBox(
        "PDF creado correctamente.`n`n"
        archivoPDF
        . "`n`nCapturas incluidas: " cantidad
    )

    return true
}