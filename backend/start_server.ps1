$proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", "cd 'C:\Users\hp\OneDrive\Documents\FAANG companies\TaskBridge\backend' && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000" -NoNewWindow -PassThru
Start-Sleep -Seconds 3
$response = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -UseBasicParsing -ErrorAction SilentlyContinue
if ($response) {
    Write-Output "Backend is running on http://127.0.0.1:8000"
    $response.Content
} else {
    Write-Output "Backend started but not responding"
}