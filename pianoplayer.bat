@ECHO OFF
REM ----------------------------------------------------------
REM             Windows-10 users:
REM      Place this file on your desktop.
REM
REM   Double clicking it will open up a GUI
REM
REM Set here the path to your Anaconda or Python installation:
REM
SET anaconda_path="C:\ProgramData\anaconda3"
REM
REM ----------------------------------------------------------



ECHO Starting pianoplayer...
CALL "%anaconda_path%\Scripts\activate"
python "%anaconda_path%\Scripts\pianoplayer" %*
ECHO Closing window...
REM PAUSE
