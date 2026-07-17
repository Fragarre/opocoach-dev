param(
    [Parameter(Mandatory = $true)]
    [string]$Salida
)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

try {
    if (-not [System.Windows.Forms.Clipboard]::ContainsImage()) {
        Write-Error "El portapapeles no contiene una imagen."
        exit 1
    }

    $imagen = [System.Windows.Forms.Clipboard]::GetImage()

    if ($null -eq $imagen) {
        Write-Error "No se ha podido leer la imagen."
        exit 2
    }

    $carpeta = Split-Path -Parent $Salida

    if (-not (Test-Path $carpeta)) {
        New-Item -ItemType Directory -Path $carpeta -Force | Out-Null
    }

    $codecJpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() |
        Where-Object { $_.MimeType -eq "image/jpeg" } |
        Select-Object -First 1

    $parametros = New-Object System.Drawing.Imaging.EncoderParameters(1)
    $calidad = New-Object System.Drawing.Imaging.EncoderParameter(
        [System.Drawing.Imaging.Encoder]::Quality,
        [long]88
    )

    $parametros.Param[0] = $calidad

    $imagen.Save($Salida, $codecJpeg, $parametros)

    $calidad.Dispose()
    $parametros.Dispose()
    $imagen.Dispose()

    exit 0
}
catch {
    Write-Error $_
    exit 10
}