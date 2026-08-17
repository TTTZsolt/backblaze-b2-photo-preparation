Set-Location -Path $PSScriptRoot
python takeout_b2_teljes_egyeztetes.py | Tee-Object -FilePath "futtatas_eredmeny.txt"
