# launcher.ps1 - Professional launcher
Write-Host "Initializing FolkDrive Billing System..." -ForegroundColor Green

# Set working directory
Set-Location "D:\Folkdrivebilling"

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "❌ Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run the setup first." -ForegroundColor Yellow
    timeout /t 5
    exit
}

# Activate virtual environment
.\venv\Scripts\Activate.ps1
Write-Host "✅ Virtual environment activated" -ForegroundColor Green

# Check if Django is available
try {
    $null = python -c "import django; print('Django available')"
    Write-Host "✅ Django is ready" -ForegroundColor Green
} catch {
    Write-Host "❌ Django not available" -ForegroundColor Red
    timeout /t 5
    exit
}

# Open browser after 2 seconds
Write-Host "🌐 Opening application in browser..." -ForegroundColor Cyan
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:8000/"

# Start Django server
Write-Host "🚀 Starting Django development server..." -ForegroundColor Yellow
Write-Host "💡 Press Ctrl+C in this window to stop the server" -ForegroundColor Magenta
Write-Host "=" * 50 -ForegroundColor White
