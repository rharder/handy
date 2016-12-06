

Private Sub Application_Startup()
  ' App starts
End Sub

Private Sub Application_Quit()
  ' App quits
End Sub



Private Sub Application_NewMail()
    ' New mail arrives
End Sub


'
' Reading email
'
Public Sub GetCurrentEmailInfo()
    Dim Session As Outlook.NameSpace
    Dim Inbox As Folder

    Dim currentItem As Object
    Dim currentMail As MailItem
    Dim report As String
    Dim subject As String
    Dim from As String
    Dim numUnread As Integer
    Dim i As Integer
    Dim froms As New Collection
    Dim subjs As New Collection
    Dim blDimensioned As Boolean    'Is the array dimensioned?
    blDimensioned = False

    Set Session = Application.Session
    Set Inbox = Session.GetDefaultFolder(olFolderInbox)

    Debug.Print ("GetCurrentEmailInfo: Inspecting Inbox...")
    For Each currentItem In Inbox.Items
        DoEvents

On Error GoTo SkipMessage

        If currentItem.Class = olMail Then
            Set currentMail = currentItem
            DoEvents

            If currentMail.UnRead = True Then
                DoEvents

                numUnread = numUnread + 1
                from = currentMail.SenderName
                subject = currentMail.subject


                ' Add to list of new email
                froms.Add (from)
                subjs.Add (subject)
                Debug.Print "Adding message from " & from & ": " & subject

            End If

        End If
SkipMessage:
    Next currentItem
On Error GoTo EndSub

    Debug.Print ("GetCurrentEmailInfo: Writing to serial...")

    report = report & "Num unread: " & numUnread

    For i = froms.Count - 1 To froms.Count
        If (i > 0) Then
            ' Call Serial_SendEmail(CStr(froms.Item(i)), CStr(subjs.Item(i)))
        End If
    Next i

EndSub:
    ' SerialClose
    Debug.Print ("GetCurrentEmailInfo: Done.")
End Sub


'
' Timers
'
Private Declare Sub Sleep Lib "kernel32" (ByVal dwMilliseconds As Long)
Public Declare Function SetTimer Lib "user32" (ByVal hwnd As Long, ByVal nIDEvent As Long, ByVal uElapse As Long, ByVal lpTimerfunc As Long) As LongPtr
Public Declare Function KillTimer Lib "user32" (ByVal hwnd As Long, ByVal nIDEvent As Long) As LongPtr
Public TimerID As Long 'Need a timer ID to eventually turn off the timer. If the timer ID <> 0 then the timer is running

Public Sub ActivateTimer(ByVal nMinutes As Long)
  nMinutes = nMinutes * 1000 * 60 'The SetTimer call accepts milliseconds, so convert to minutes
  If TimerID <> 0 Then Call DeactivateTimer 'Check to see if timer is running before call to SetTimer
  TimerID = SetTimer(0, 0, nMinutes, AddressOf TriggerTimer)
  If TimerID = 0 Then
    MsgBox "The timer failed to activate."
  End If
End Sub

Public Sub DeactivateTimer()
Dim lSuccess As Long
  lSuccess = KillTimer(0, TimerID)
  If lSuccess = 0 Then
    MsgBox "The timer failed to deactivate."
  Else
    TimerID = 0
  End If
End Sub

Public Sub TriggerTimer(ByVal hwnd As Long, ByVal uMsg As Long, ByVal idevent As Long, ByVal Systime As Long)
  'MsgBox "The TriggerTimer function has been automatically called!"
End Sub
