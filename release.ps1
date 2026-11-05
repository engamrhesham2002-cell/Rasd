# Rasd - one-click GitHub release (Windows PowerShell 5.1+)
# Builds the app, packs it into RasdSetup.exe with NSIS, pushes main,
# creates the tag + release, and uploads the installer for the in-app updater.
param(
    [switch]$SkipBuild,
    [switch]$SkipPush,
    [switch]$Draft,
    [switch]$Yes
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root       = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Owner       = 'engamrhesham2002-cell'
$Repo        = 'Rasd'
$Branch      = 'main'
$ApiBase     = "https://api.github.com/repos/$Owner/$Repo"
$TokenFile   = Join-Path $env:LOCALAPPDATA 'Rasd\github_token.txt'
$NotesPath   = Join-Path $Root 'RELEASE_NOTES.md'
$DistDir     = Join-Path $Root 'dist\Rasd'
$NsiPath     = Join-Path $Root 'build_installer.nsi'
$AssetDir    = Join-Path $Root 'release'
$AssetName   = 'RasdSetup.exe'
$Installer   = Join-Path $AssetDir $AssetName
$MaxAssetSize = 350MB

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
        if ($err.ErrorDetails -and $err.ErrorDetails.Message) { return $err.ErrorDetails.Message }
    } catch { }
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

function Find-Makensis {
    $cmd = Get-Command makensis -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $bases = @($env:ProgramFiles, ${env:ProgramFiles(x86)}, (Join-Path $env:LOCALAPPDATA 'Programs'))
    foreach ($base in $bases) {
        if (-not $base) { continue }
        $candidate = Join-Path $base 'NSIS\makensis.exe'
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
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
Write-Host '  Rasd - Create GitHub Release (Setup EXE)' -ForegroundColor White
Write-Host '============================================' -ForegroundColor DarkGray

if (-not (Test-Path (Join-Path $Root 'config.py'))) { Fail 'config.py not found. Run this file from the Rasd folder.' }
if (-not (Test-Path (Join-Path $Root '.git'))) { Fail 'This folder is not a Git repository.' }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fail 'Git is not installed or not in PATH.' }
if (-not (Test-Path $NotesPath)) { Fail 'RELEASE_NOTES.md not found.' }
if (-not (Test-Path $NsiPath)) { Fail 'build_installer.nsi not found.' }

$versionMatch = Select-String -Path (Join-Path $Root 'config.py') -Pattern "APP_VERSION\s*=\s*'([^']+)'" | Select-Object -First 1
if (-not $versionMatch) { Fail 'APP_VERSION not found in config.py.' }
$version   = $versionMatch.Matches[0].Groups[1].Value
$tag       = $version
$nsisVer   = $version -replace '^[vV]', ''
$makensis  = Find-Makensis

if (-not $makensis) {
    Fail @'
NSIS (makensis) is not installed.
Install it once from https://nsis.sourceforge.io/Download
or run this in PowerShell:  winget install -e --id NSIS.NSIS
Then run release.bat again.
'@
}

# Read as a plain .NET string: Get-Content -Raw attaches provider note
# properties (PSPath/ReadCount/...) that ConvertTo-Json turns into a huge object.
$notes = [System.IO.File]::ReadAllText($NotesPath, [System.Text.Encoding]::UTF8)
$title = (($notes -split '\r?\n', 2)[0]) -replace '^#\s*', ''
if (-not $title) { $title = "Rasd $version" }

Write-Host ''
Write-Host "  Version  : $version" -ForegroundColor Gray
Write-Host "  Repo     : $Owner/$Repo" -ForegroundColor Gray
Write-Host "  Asset    : $AssetName" -ForegroundColor Gray
Write-Host "  Tag      : $tag" -ForegroundColor Gray
Write-Host "  NSIS     : $makensis" -ForegroundColor Gray

# ---------------------------------------------------------------- auth
Write-Step 'Checking GitHub access'
$token = Read-Token
if (-not $token) { Fail 'No GitHub token available.' }

$script:headers = @{
    Authorization          = "Bearer $token"
    Accept                 = 'application/vnd.github+json'
    'User-Agent'           = 'Rasd-Release'
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

# ---------------------------------------------------------------- build app
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
    Write-Host "  1. Build $AssetName with NSIS (version $nsisVer)"
    if (-not $SkipPush) {
        Write-Host "  2. Commit local changes and push to $Branch"
        Write-Host "  3. Create tag $tag and GitHub release"
    } else {
        Write-Host "  2. (push skipped) Create tag $tag and GitHub release"
    }
    Write-Host "  4. Upload $AssetName as the release asset"
    Write-Host ''
    $go = Read-Host 'Continue? (Y/n)'
    if ($go -match '^(n|no)$') {
        Write-Host 'Cancelled. Nothing was published.' -ForegroundColor Yellow
        exit 0
    }
}

# ---------------------------------------------------------------- installer
Write-Step "Building $AssetName with NSIS"
if (-not (Test-Path $AssetDir)) { New-Item -ItemType Directory -Path $AssetDir -Force | Out-Null }
if (Test-Path $Installer) { Remove-Item $Installer -Force }

& $makensis "/DAPP_VERSION=$nsisVer" "/DROOT=$Root" $NsiPath
if ($LASTEXITCODE -ne 0) { Fail 'NSIS failed to build the installer. Read the messages above.' }
if (-not (Test-Path $Installer)) { Fail "NSIS finished but $Installer was not created." }

$installerFile = Get-Item $Installer
if ($installerFile.Length -le 0) { Fail 'The installer file is empty.' }
if ($installerFile.Length -gt $MaxAssetSize) {
    Fail ("The installer is {0:N1} MB, but the in-app updater accepts at most 350 MB." -f ($installerFile.Length / 1MB))
}

$stream = [System.IO.File]::OpenRead($Installer)
try {
    $sig = New-Object byte[] 2
    $null = $stream.Read($sig, 0, 2)
} finally {
    $stream.Dispose()
}
if ($sig[0] -ne 0x4D -or $sig[1] -ne 0x5A) { Fail 'The installer is not a valid Windows EXE (missing MZ header).' }

$hash = (Get-FileHash -Path $Installer -Algorithm SHA256).Hash.ToLower()
Write-Ok ("Created {0} ({1:N1} MB)" -f $installerFile.Name, ($installerFile.Length / 1MB))
Write-Ok "SHA-256: $hash"

# ---------------------------------------------------------------- git
if (-not $SkipPush) {
    Write-Step 'Pushing source code to GitHub'

    git remote get-url origin *> $null
    if ($LASTEXITCODE -ne 0) {
        git remote add origin "https://github.com/$Owner/$Repo.git"
        if ($LASTEXITCODE -ne 0) { Fail 'Could not add the GitHub remote.' }
        Write-Ok 'Added remote origin'
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

$release = $null
try {
    $release = Invoke-RestMethod -Uri "$ApiBase/releases/tags/$tag" -Headers $script:headers -Method Get
    Write-Ok "Release already exists, updating it (id $($release.id))"
} catch {
    $status = 0
    try { $status = [int]$_.Exception.Response.StatusCode } catch { }
    if ($status -ne 404) { Fail "Could not check the existing release. $(Get-ApiError $_)" }
}

$payloadJson = @{
    tag_name   = $tag
    name       = $title
    body       = $notes
    draft      = [bool]$Draft
    prerelease = $false
} | ConvertTo-Json -Depth 5

# Windows PowerShell 5.1 sends a plain string body using the ANSI code page,
# which turns Arabic into invalid UTF-8 and makes GitHub reject it with 400.
# Sending explicit UTF-8 bytes keeps the release notes readable.
$payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payloadJson)

if ($release) {
    try {
        $release = Invoke-RestMethod -Uri "$ApiBase/releases/$($release.id)" -Headers $script:headers -Method Patch -Body $payloadBytes -ContentType 'application/json; charset=utf-8'
    } catch {
        Fail "Could not update the existing release. $(Get-ApiError $_)"
    }
} else {
    try {
        $release = Invoke-RestMethod -Uri "$ApiBase/releases" -Headers $script:headers -Method Post -Body $payloadBytes -ContentType 'application/json; charset=utf-8'
    } catch {
        Fail "Could not create the release. $(Get-ApiError $_)"
    }
}
Write-Ok "Release ready: $($release.html_url)"

# ---------------------------------------------------------------- asset
Write-Step "Uploading $AssetName"
$existing = @($release.assets) | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1
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
$uploadUri  = "$uploadBase?name=$([uri]::EscapeDataString($AssetName))"

try {
    $asset = Invoke-RestMethod -Uri $uploadUri -Headers $script:headers -Method Post `
        -ContentType 'application/x-msdownload' -InFile $Installer -TimeoutSec 1800
    Write-Ok ("Uploaded {0:N1} MB" -f ($asset.size / 1MB))
} catch {
    Fail "Upload failed. The release exists but has no asset. Re-run release.bat to retry. $(Get-ApiError $_)"
}

# ---------------------------------------------------------------- cleanup
# The in-app updater takes the FIRST .exe asset. Keep exactly one EXE and drop
# legacy ZIP assets so users never download the wrong file.
Write-Step 'Cleaning up extra release assets'
try {
    $fresh = Invoke-RestMethod -Uri "$ApiBase/releases/$($release.id)" -Headers $script:headers -Method Get
    $extras = @($fresh.assets) | Where-Object {
        $_.name -ne $AssetName -and ($_.name -match '\.(exe|zip)$')
    }
    if (-not $extras) {
        Write-Ok "Only $AssetName is attached."
    } else {
        foreach ($extra in $extras) {
            Write-Warn "Removing extra asset: $($extra.name)"
            try {
                Invoke-RestMethod -Uri "$ApiBase/releases/assets/$($extra.id)" -Headers $script:headers -Method Delete | Out-Null
                Write-Ok "Removed $($extra.name)"
            } catch {
                Write-Warn "Could not remove $($extra.name): $(Get-ApiError $_)"
            }
        }
    }
} catch {
    Write-Warn "Could not check extra assets: $(Get-ApiError $_)"
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
