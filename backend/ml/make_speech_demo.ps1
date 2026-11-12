# Synthetic speech only: do not use this script to record personal audio.
Add-Type -AssemblyName System.Speech
$demoDirectory = Join-Path $PSScriptRoot '../data/raw/media_demo'
New-Item -ItemType Directory -Force $demoDirectory | Out-Null
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speaker.SetOutputToWaveFile((Join-Path $demoDirectory 'synthetic-speech.wav'))
    $speaker.Speak('This is a synthetic demonstration. Send your password now to claim a prize.')
} finally {
    $speaker.Dispose()
}
Write-Output 'Synthetic speech generated; no personal audio recorded.'
