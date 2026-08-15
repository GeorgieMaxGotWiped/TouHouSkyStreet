<#
    download_wiki_image.ps1
    Downloads the first image found on a Hypixel SkyBlock Wiki page.
    Usage:
        powershell -ExecutionPolicy Bypass -File .\download_wiki_image.ps1
        powershell -ExecutionPolicy Bypass -File .\download_wiki_image.ps1 -Url "https://hypixelskyblock.minecraft.wiki/wiki/Some_Page" -OutDir "D:\pyz\my thingses\TouHou\assets\wiki"
#>
param(
    [string]$Url = "https://hypixelskyblock.minecraft.wiki/",
    [string]$OutDir = "D:\pyz\my thingses\TouHou\assets\wiki"
)

$ErrorActionPreference = "Stop"

# Force TLS 1.2+ (needed on older Windows PowerShell 5.1)
[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

$outDirFull = [IO.Path]::GetFullPath($OutDir)
New-Item -ItemType Directory -Force -Path $outDirFull | Out-Null

$ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

Write-Host "Fetching page: $Url"
$resp = Invoke-WebRequest -Uri $Url -UseBasicParsing -Headers @{ "User-Agent" = $ua }
$html = $resp.Content

$imgPattern = 'https?://[^"'']+?\.(?:png|jpe?g|gif|webp)[^"'']*'
$candidates = [regex]::Matches($html, $imgPattern, 'IgnoreCase') | ForEach-Object { $_.Value }

# Prefer real uploads under /images/ or thumbnails /thumb/
$chosen = $candidates | Where-Object { $_ -match '/images/|/thumb/' } | Select-Object -First 1
if (-not $chosen) { $chosen = $candidates | Select-Object -First 1 }
if (-not $chosen) { throw "No image URL found on the page: $Url" }

$fileName = [IO.Path]::GetFileName(($chosen -split '\?')[0])
if (-not $fileName) { $fileName = "downloaded_image.png" }
$dest = Join-Path $outDirFull $fileName

Write-Host "Downloading: $chosen"
Invoke-WebRequest -Uri $chosen -UseBasicParsing -OutFile $dest -Headers @{ "User-Agent" = $ua }

Write-Host "Saved to : $dest"
Write-Host ("File size: {0:N0} bytes" -f (Get-Item -LiteralPath $dest).Length)
