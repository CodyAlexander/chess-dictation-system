# Chess Dictation System
## Objective
Provide the ability for a user to dictate notation to move pieces in chess applications.

## High-Level Architecture
* Poll the screen for screenshots at 1s intervals
  * tkinter library
* Retrieve the FEN from screenshots of chess applications
  * Tensorflow model and tool library created by Elucidation:  https://github.com/Elucidation/tensorflow_chessbot/tree/chessfenbot
* Load the FEN into an internal chess game
  * python-chess library
* Push-to-talk, listen for dictated chess notation
  * SpeechRecognition library using PocketSphinx
* Execute move on screen
  * Pyautogui library
