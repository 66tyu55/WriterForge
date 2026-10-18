# Launch WriterForge's OWN read-only Cloudflare Worker client.
# Never print, write to disk or send the API token to GitHub.
# This script is optional; it does not run git, GitHub Actions or deployments.
param(
    [string]$Endpoint = "https://wf-r2-api.3227482831.workers.dev"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$secret = Read-Host -Prompt "WF_API_TOKEN (hidden input)" -AsSecureString
$ptr = [IntPtr]::Zero

try {
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
    $env:WF_API_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    Push-Location $projectRoot
    try {
        Write-Host "WriterForge is invoking its own Cloudflare Worker HTTP client..."
        python -m writerforge.cli r2-http-inventory --endpoint $Endpoint
        if ($LASTEXITCODE -ne 0) {
            throw "WriterForge HTTP invocation failed (Python exit code $LASTEXITCODE)."
        }
    } finally {
        Pop-Location
    }
} finally {
    Remove-Item Env:\WF_API_TOKEN -ErrorAction SilentlyContinue
    if ($ptr -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
    $secret.Dispose()
}
