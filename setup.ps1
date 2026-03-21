# ============================================================
# GEO-SEO Tool Setup for Windows (Antigravity / Gemini CLI)
# ============================================================

Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   GEO-SEO Tool — Windows Setup           ║" -ForegroundColor Cyan
Write-Host "║   AI Search Optimization for Any Agent    ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---- Check Python ----
Write-Host "→ Checking prerequisites..." -ForegroundColor Blue

$pythonCmd = $null
try {
    $ver = & python --version 2>&1
    if ($ver -match "Python 3\.(\d+)") {
        if ([int]$Matches[1] -ge 8) {
            $pythonCmd = "python"
            Write-Host "✓ $ver" -ForegroundColor Green
        }
    }
} catch {}

if (-not $pythonCmd) {
    Write-Host "✗ Python 3.8+ is required but not found." -ForegroundColor Red
    Write-Host "  Install: https://www.python.org/downloads/"
    exit 1
}

# ---- Create Virtual Environment ----
Write-Host "→ Creating virtual environment..." -ForegroundColor Blue

$venvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path $venvPath)) {
    & $pythonCmd -m venv $venvPath
    Write-Host "✓ Virtual environment created at .venv/" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
}

# Activate venv
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
. $activateScript

# ---- Install Dependencies ----
Write-Host "→ Installing Python dependencies..." -ForegroundColor Blue

$reqFile = Join-Path $ProjectRoot "requirements.txt"
& python -m pip install --upgrade pip --quiet 2>$null
& python -m pip install -r $reqFile --quiet 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Python dependencies installed" -ForegroundColor Green
} else {
    Write-Host "⚠ Some dependencies failed. Run manually:" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\activate && pip install -r requirements.txt"
}

# ---- Optional: Playwright ----
Write-Host ""
$installPlaywright = Read-Host "Install Playwright for screenshots? (y/n)"
if ($installPlaywright -eq "y" -or $installPlaywright -eq "Y") {
    Write-Host "→ Installing Playwright browsers..." -ForegroundColor Blue
    & python -m playwright install chromium 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Playwright Chromium installed" -ForegroundColor Green
    } else {
        Write-Host "⚠ Playwright installation failed. Screenshots won't be available." -ForegroundColor Yellow
    }
}

# ---- Verify ----
Write-Host ""
Write-Host "→ Verifying installation..." -ForegroundColor Blue

$checks = @(
    @{ Path = (Join-Path $ProjectRoot "geo\SKILL.md"); Label = "Main GEO skill" },
    @{ Path = (Join-Path $ProjectRoot "skills\geo-audit\SKILL.md"); Label = "Audit sub-skill" },
    @{ Path = (Join-Path $ProjectRoot "scripts\full_audit.py"); Label = "Hybrid orchestrator" },
    @{ Path = (Join-Path $ProjectRoot "scripts\fetch_page.py"); Label = "Fetch script" },
    @{ Path = (Join-Path $ProjectRoot "scripts\citability_scorer.py"); Label = "Citability scorer" },
    @{ Path = (Join-Path $ProjectRoot "scripts\generate_pdf_report.py"); Label = "PDF generator" }
)

$allOk = $true
foreach ($check in $checks) {
    if (Test-Path $check.Path) {
        Write-Host "✓ $($check.Label)" -ForegroundColor Green
    } else {
        Write-Host "✗ $($check.Label) missing" -ForegroundColor Red
        $allOk = $false
    }
}

# ---- Summary ----
Write-Host ""
Write-Host "╔══════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║        Setup Complete!                    ║" -ForegroundColor Green
Write-Host "╚══════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "  Project:    $ProjectRoot"
Write-Host "  Venv:       .venv\"
Write-Host "  Activate:   .venv\Scripts\activate"
Write-Host ""
Write-Host "Usage:" -ForegroundColor Blue
Write-Host "  1. Open this folder in Antigravity / Gemini CLI"
Write-Host "  2. Ask: 'Generate the GEO PDF report for https://example.com'"
Write-Host ""
Write-Host "  See USAGE.md for full documentation."
Write-Host ""
