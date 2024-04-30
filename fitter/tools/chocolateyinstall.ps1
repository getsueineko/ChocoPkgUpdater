
$ErrorActionPreference = 'Stop';
$toolsDir   = "$(Split-Path -parent $MyInvocation.MyCommand.Definition)"
$url        = 'https://github.com/zaps166/QMPlay2/releases/download/24.04.07/QMPlay2-Win32-24.04.07-qt5-offline.exe'
$url64      = 'https://github.com/zaps166/QMPlay2/releases/download/24.04.07/QMPlay2-Win64-24.04.07-qt5-offline.exe'

$packageArgs = @{
  packageName   = $env:ChocolateyPackageName
  unzipLocation = $toolsDir
  fileType      = 'exe'
  url           = $url
  url64bit      = $url64

  softwareName  = 'qmplay2*'

  checksum      = '3e5b34f5649c5829edc819fad2e747c86556ea60d8748a24999324809975086a'
  checksumType  = 'sha256'
  checksum64    = 'c476bce45a60b211d7839cd83689e23b4dbf0a3b77b8fb41284ad05a6006a3a8'
  checksumType64= 'sha256'

  silentArgs   = '--Auto'
}

Install-ChocolateyPackage @packageArgs