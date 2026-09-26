# Esporta in PDF un .docx con Microsoft Word, per controllare l'impaginazione reale.
param([string]$Docx, [string]$Pdf)
$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open((Resolve-Path $Docx).Path, $false, $true)
    $doc.ExportAsFixedFormat($Pdf, 17)   # 17 = wdExportFormatPDF
    "Pagine: " + $doc.ComputeStatistics(2)   # 2 = wdStatisticPages
    $doc.Close($false)
} finally {
    $word.Quit()
}
