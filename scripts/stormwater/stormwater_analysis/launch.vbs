' ===========================================================================
' Stormwater Analysis Tools - launcher
'
' Double-click this file to start the application.
'
' Runs the tool with ArcGIS Pro's Python using pythonw.exe, so no console
' window appears. ArcGIS Pro must be installed and you must be signed in.
'
' Place this file in the same folder as stormwater_analysis.py.
' ===========================================================================

Option Explicit

Dim fso, shell, base, scriptPath, pyw, candidates, i, msg

Set fso   = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

base       = fso.GetParentFolderName(WScript.ScriptFullName)
scriptPath = fso.BuildPath(base, "stormwater_analysis.py")

' If auto-detection ever fails on a machine, hard-code the pythonw.exe path
' on the next line and it will be used instead of the search below.
pyw = ""

If pyw = "" Then
    candidates = Array( _
        shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe"), _
        "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe", _
        shell.ExpandEnvironmentStrings("%PROGRAMFILES%\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\pythonw.exe"), _
        shell.ExpandEnvironmentStrings("%LOCALAPPDATA%\ESRI\conda\envs\arcgispro-py3\pythonw.exe") _
    )
    For i = 0 To UBound(candidates)
        If fso.FileExists(candidates(i)) Then
            pyw = candidates(i)
            Exit For
        End If
    Next
End If

If pyw = "" Then
    msg = "Could not find ArcGIS Pro's Python." & vbCrLf & vbCrLf & _
          "This tool requires ArcGIS Pro to be installed." & vbCrLf & _
          "If Pro is installed in a non-standard location, contact GIS."
    MsgBox msg, vbCritical, "Stormwater Analysis Tools"
    WScript.Quit 1
End If

If Not fso.FileExists(scriptPath) Then
    msg = "Could not find stormwater_analysis.py." & vbCrLf & vbCrLf & _
          "Expected it here:" & vbCrLf & scriptPath & vbCrLf & vbCrLf & _
          "Make sure the whole folder was copied, not just this file."
    MsgBox msg, vbCritical, "Stormwater Analysis Tools"
    WScript.Quit 1
End If

' 1 = normal window, False = do not wait for it to exit
shell.Run """" & pyw & """ """ & scriptPath & """", 1, False