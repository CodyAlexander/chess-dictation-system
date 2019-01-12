# Chess Dictation System
## Objective
Provide the ability for a user to dictate notation to move pieces in chess applications.

## High-Level Architecture
* Poll the screen for screenshots at 1s intervals
* Retrieve the FEN from screenshots of chess applications
  * Qualify specific chess applications
  * Start with chess.com Puzzle Rush
* Load the FEN into an internal chess game
* Push-to-talk, listen for dictated chess notation
* Determine starting square, end square based on chess notation
* Determine location of starting square, end square on screen
* Click starting square, click end square on screen
