param([Parameter(Mandatory=$true)][string]$Source,
      [Parameter(Mandatory=$true)][string]$Destination)
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
$code = 0
try {
    try { $word = New-Object -ComObject Word.Application }
    catch { exit 20 }
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3 # Désactiver les macros des documents ouverts.
    $word.Options.UpdateLinksAtOpen = $false
    # ConfirmConversions=false, ReadOnly=true, AddToRecentFiles=false,
    # PasswordDocument fourni pour éviter une demande interactive.
    $document = $word.Documents.Open($Source, $false, $true, $false, '__no_password__')
    $document.ExportAsFixedFormat($Destination, 17)
} catch {
    $code = 21
} finally {
    if ($null -ne $document) {
        try { $document.Close(0) } catch {}
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document)
    }
    if ($null -ne $word) {
        try { $word.Quit(0) } catch {}
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($word)
    }
}
exit $code
