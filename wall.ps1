$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir\deskpat_src\deskpat.py" $args
