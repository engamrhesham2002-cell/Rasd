# Rasd - one-click GitHub release (Windows PowerShell 5.1+)
# Builds (optional), zips dist\Rasd, pushes main, creates tag + release, uploads asset.
param(
    [switch]$SkipBuild,
    [switch]$SkipPush,
    [switch]$Draft,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root      = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Owner     = 'engamrhesham2002-cell'
$Repo      = 'Rasd'
$Branch    = 'main'
$ApiBase   = "https://api.github.com/repos/$Owner/$Repo"
$TokenFile = Join-Path $env:LOCALAPPDATA 'Rasd\github_token.txt'
$NotesPath = Join-Path $Root 'RELEASE_NOTES.md'
$DistDir   = Join-Path $Root 'dist\Rasd'
$AssetDir  = Join-Path $Root 'release'

function Write-Step([string]$Text) {
    Write-Host ''
    Write-Host "==> $Text" -ForegroundColor Cyan
}
function Write-Ok([string]$Text)   { Write-Host "    $Text" -ForegroundColor Green }
function Write-Warn([string]$Text) { Write-Host "    $Text" -ForegroundColor Yellow }
function Fail([string]$Text) {
    Write-Host ''
    Write-Host "ERROR: $Text" -ForegroundColor Red
    exit 1
}

function Get-ApiError($err) {
    try {
        $resp = $err.Exception.Response
        if ($resp) {
            $stream = $resp.GetResponseStream()
            if ($stream) {
                $reader = New-Object System.IO.StreamReader($stream)
                $text = $reader.ReadToEnd()
                if ($text) { return "HTTP $([int]$resp.StatusCode): $text" }
            }
        }
    } catch { }
    return $err.Exception.Message
}

function Read-Token {
    foreach ($name in @('RASD_GH_TOKEN', 'GH_TOKEN', 'GITHUB_TOKEN')) {
        $value = [Environment]::GetEnvironmentVariable($name)
        if ($value) { return $value.Trim() }
    }
    if (Test-Path $TokenFile) {
        $value = (Get-Content -Raw -Encoding UTF8 $TokenFile).Trim()
        if ($value) { return $value }
    }

    Write-Host ''
    Write-Host 'A GitHub token is required (classic token with "repo" scope,' -ForegroundColor Yellow
    Write-Host 'or fine-grained token with Contents: Read and write).' -ForegroundColor Yellow
    Write-Host 'Create one here: https://github.com/settings/tokens' -ForegroundColor Yellow
    Write-Host ''
    $secure = Read-Host 'Paste your GitHub token (input is hidden)' -AsSecureString
    if (-not $secure) { Fail 'No token provided.' }
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try { $value = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr).Trim() }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
    if (-not $value) { Fail 'No token provided.' }

    Write-Host ''
    $save = Read-Host 'Save the token on this PC for next time? (y/N)'
    if ($save -match '^(y|yes)$') {
        $dir = Split-Path -Parent $TokenFile
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Set-Content -Path $TokenFile -Value $value -Encoding UTF8 -NoNewline
        Write-Ok "Saved to $TokenFile"
        Write-Warn 'Keep this file private. You can delete it at any time.'
    }
    return $value
}

# ---------------------------------------------------------------- start
Write-Host ''
Write-Host '============================================' -ForegroundColor DarkGray
Write-Host '  Rasd - Create GitHub Release' -ForegroundColor White
Write-Host '============================================' -ForegroundColor DarkGray

if (-not (Test-Path (Join-Path $Root 'config.py'))) { Fail 'config.py not found. Run this file from the Rasd folder.' }
if (-not (Test-Path (Join-Path $Root '.git'))) { Fail 'This folder is not a Git repository.' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail 'Git is not installed or not in PATH.' }
if (-not (Test-Path $NotesPath)) { Fail 'RELEASE_NOTES.md not found.' }

$versionMatch = Select-String -Path (Join-Path $Root 'config.py') -Pattern "APP_VERSION\s*=\s*'([^']+)'" | Select-Object -First 1
if (-not $versionMatch) { Fail 'APP_VERSION not found in config.py.' }
$version = $versionMatch.Matches[0].Groups[1].Value
$tag     = $version
$assetName = "Rasd-$version-win64.zip"
$zipPath   = Join-Path $AssetDir $assetName

$title = (Get-Content -Encoding UTF8 $NotesPath -TotalCount 1) -replace '^#\s*', ''
if (-not $title) { $title = "Rasd $version" }

Write-Host ''
Write-Host "  Version : $version" -ForegroundColor Gray
Write-Host "  Repo    : $Owner/$Repo" -ForegroundColor Gray
Write-Host "  Asset   : $assetName" -ForegroundColor Gray
Write-Host "  Tag     : $tag" -ForegroundColor Gray

# ---------------------------------------------------------------- auth
Write-Step 'Checking GitHub access'
$token = Read-Token
if (-not $token) { Fail 'No GitHub token available.' }

$script:headers = @{
    Authorization        = "Bearer $token"
    Accept               = 'application/vnd.github+json'
    'User-Agent'         = 'Rasd-Release'
    'X-GitHub-Api-Version' = '2022-11-28'
}

try {
    $me = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $script:headers -Method Get
    Write-Ok "Signed in as $($me.login)"
} catch {
    Fail "GitHub rejected the token. $(Get-ApiError $_)"
}

try {
    $repoInfo = Invoke-RestMethod -Uri $ApiBase -Headers $script:headers -Method Get
    Write-Ok "Repository: $($repoInfo.full_name)"
} catch {
    Fail "Cannot access $Owner/$Repo. $(Get-ApiError $_)"
}

if ($repoInfo.permissions -and -not ($repoInfo.permissions.push -or $repoInfo.permissions.admin)) {
    Fail 'This token does not have write access to the repository.'
}

# ---------------------------------------------------------------- build
$rebuild = $false
if (-not $SkipBuild) {
    if (-not (Test-Path (Join-Path $DistDir 'Rasd.exe'))) {
        Write-Warn 'dist\Rasd\Rasd.exe not found, a build is required.'
        $rebuild = $true
    } elseif ($Yes) {
        $rebuild = $false
    } else {
        $exe = Get-Item (Join-Path $DistDir 'Rasd.exe')
        Write-Host ''
        Write-Host "  Current EXE: $($exe.LastWriteTime.ToString('yyyy-MM-dd HH:mm'))" -ForegroundColor Gray
        $answer = Read-Host 'Rebuild the app before releasing? (y/N)'
        if ($answer -match '^(y|yes)$') { $rebuild = $true }
    }
}

if ($rebuild) {
    Write-Step 'Building the application (this can take several minutes)'
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & py -3.11 -m PyInstaller Rasd.spec --noconfirm --clean
    } else {
        & python -m PyInstaller Rasd.spec --noconfirm --clean
    }
    if ($LASTEXITCODE -ne 0) { Fail 'Build failed. Check the messages above.' }
    if (-not (Test-Path (Join-Path $DistDir 'Rasd.exe'))) { Fail 'Build finished but dist\Rasd\Rasd.exe was not created.' }
    Write-Ok 'Build finished.'
}

if (-not (Test-Path (Join-Path $DistDir 'Rasd.exe'))) {
    Fail 'dist\Rasd\Rasd.exe not found. Run build.bat first or remove -SkipBuild.'
}

# ---------------------------------------------------------------- confirm
if (-not $Yes) {
    Write-Host ''
    Write-Host 'About to:' -ForegroundColor White
    Write-Host "  1. Compress dist\Rasd into release\$assetName"
    if (-not $SkipPush) {
        Write-Host "  2. Commit local changes and push to $Branch"
        Write-Host "  3. Create tag $tag and GitHub release"
    } else {
        Write-Host "  2. (push skipped) Create tag $tag and GitHub release"
    }
    Write-Host '  4. Upload the ZIP as a release asset'
    Write-Host ''
    $go = Read-Host 'Continue? (Y/n)'
    if ($go -match '^(n|no)$') {
        Write-Host 'Cancelled. Nothing was published.' -ForegroundColor Yellow
        exit 0
    }
}

# ---------------------------------------------------------------- zip
Write-Step "Compressing dist\Rasd into release\$assetName"
if (-not (Test-Path $AssetDir)) { New-Item -ItemType Directory -Path $AssetDir -Force | Out-Null }
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Add-Type -AssemblyName System.IO.Compression.FileSystem
try {
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        (Resolve-Path $DistDir).Path, $zipPath,
        [System.IO.Compression.CompressionLevel]::Optimal, $true)
} catch {
    Write-Warn "Fast zip failed, using Compress-Archive instead..."
    Compress-Archive -Path (Resolve-Path $DistDir).Path -DestinationPath $zipPath -CompressionLevel Optimal -Force
}

$zipFile = Get-Item $zipPath
Write-Ok ("Created {0} ({1:N1} MB)" -f $zipFile.Name, ($zipFile.Length / 1MB))

$reader = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
try {
    $hasExe = $reader.Entries | Where-Object { $_.FullName -eq 'Rasd/Rasd.exe' } | Select-Object -First 1
} finally {
    $reader.Dispose()
}
if (-not $hasExe) { Fail 'The ZIP does not contain Rasd/Rasd.exe. Release aborted.' }
Write-Ok 'ZIP structure verified: Rasd/Rasd.exe'

# ---------------------------------------------------------------- git
if (-not $SkipPush) {
    Write-Step 'Pushing source code to GitHub'

    git remote get-url origin *> $null
    if ($LASTEXITCODE -ne 0) {
        git remote add origin "https://github.com/$Owner/$Repo.git"
        if ($LASTEXITCODE -ne 0) { Fail 'Could not add the GitHub remote.' }
        Write-Ok "Added remote origin"
    }

    git add -A
    git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        git commit -m "Release $version" *> $null
        if ($LASTEXITCODE -ne 0) { Fail 'Could not create the commit.' }
        Write-Ok "Committed local changes as 'Release $version'"
    } else {
        Write-Ok 'No local changes to commit.'
    }

    git push origin "HEAD:$Branch"
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Warn 'Normal push was rejected (different history on GitHub?).'
        Write-Warn 'Run push.bat once to create a backup branch and replace main, then run release.bat again.'
        Fail 'Code was not pushed. No release was created.'
    }
    Write-Ok "Pushed to $Branch"
} else {
    Write-Warn 'Skipping git push (-SkipPush).'
}

# ---------------------------------------------------------------- tag
Write-Step "Creating tag $tag"
git tag -f $tag *> $null
if ($LASTEXITCODE -ne 0) { Fail "Could not create tag $tag." }
git push origin "refs/tags/$tag" --force
if ($LASTEXITCODE -ne 0) { Fail "Could not push tag $tag." }
Write-Ok "Tag $tag is on GitHub"

# ---------------------------------------------------------------- release
Write-Step 'Creating / updating the GitHub release'
if (-not (Test-Path $NotesPath)) { Fail 'RELEASE_NOTES.md not found.' }
$notes = Get-Content -Raw -Encoding UTF8 $NotesPath

$release = $null
try {
    $release = Invoke-RestMethod -Uri "$ApiBase/releases/tags/$tag" -Headers $script:headers -Method Get
    Write-Ok "Release already exists, updating it (id $($release.id))"
} catch {
    $status = 0
    try { $status = [int]$_.Exception.Response.StatusCode } catch { }
    if ($status -ne 404) { Fail "Could not check the existing release. $(Get-ApiError $_)" }
}

$payload = @{
    tag_name   = $tag
    name       = $title
    body       = $notes
    draft      = [bool]$Draft
    prerelease = $false
} | ConvertTo-Json -Depth 5

if ($release) {
    $release = Invoke-RestMethod -Uri "$ApiBase/releases/$($release.id)" -Headers $script:headers -Method Patch -Body $payload -ContentType 'application/json'
} else {
    try {
        $release = Invoke-RestMethod -Uri "$ApiBase/releases" -Headers $script:headers -Method Post -Body $payload -ContentType 'application/json'
    } catch {
        Fail "Could not create the release. $(Get-ApiError $_)"
    }
}
Write-Ok "Release ready: $($release.html_url)"

# ---------------------------------------------------------------- asset
Write-Step "Uploading $assetName"
$existing = @($release.assets) | Where-Object { $_.name -eq $assetName } | Select-Object -First 1
if ($existing) {
    Write-Warn 'An asset with the same name exists, replacing it...'
    try {
        Invoke-RestMethod -Uri "$ApiBase/releases/assets/$($existing.id)" -Headers $script:headers -Method Delete | Out-Null
    } catch {
        Fail "Could not delete the old asset. $(Get-ApiError $_)"
    }
    $release = Invoke-RestMethod -Uri "$ApiBase/releases/$($release.id)" -Headers $script:headers -Method Get
}

$uploadBase = ($release.upload_url -replace '\{.*$', '')
$uploadUri  = "$uploadBase?name=$([uri]::EscapeDataString($assetName))"

try {
    $asset = Invoke-RestMethod -Uri $uploadUri -Headers $script:headers -Method Post `
        -ContentType 'application/zip' -InFile $zipPath -TimeoutSec 1800
    Write-Ok ("Uploaded {0:N1} MB" -f ($asset.size / 1MB))
} catch {
    Fail "Upload failed. The release exists but has no asset. Re-run release.bat to retry. $(Get-ApiError $_)"
}

# ---------------------------------------------------------------- done
Write-Host ''
Write-Host '============================================' -ForegroundColor Green
Write-Host '  RELEASE PUBLISHED' -ForegroundColor Green
Write-Host '============================================' -ForegroundColor Green
Write-Host "  Release : $($release.html_url)"
Write-Host "  Download: $($asset.browser_download_url)"
Write-Host "  Tag     : $tag"
Write-Host ''
exit 0
