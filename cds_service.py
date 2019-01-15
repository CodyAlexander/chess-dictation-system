# -*- coding: utf-8 -*-
"""
@author: Cody Alexander

Python service, polls the screen to determine FEN of any detected
chess boards.

Changelog:
    2019-01-12 Cody Alexander - Created
    2019-01-15 Cody Alexander - Now using Google Cloud Speech API
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import sys
import os
import logging

import tkinter
import speech_recognition as sr
import chess
import pyautogui

sys.path.append(os.path.join(os.getcwd(), r'chessfenbot'))
import tensorflow_chessbot
import chessboard_finder
from helper_functions import shortenFEN

LOG_LEVEL = logging.DEBUG
GCP_SPEECH_LANGUAGE = "en-US"
SPEECH_API_PHRASES = [
        "black",
        "white",
        "pawn",
        "bishop",
        "knight",
        "rook",
        "queen",
        "king",
        "takes",
        "take",
        "captures",
        "capture",
        "alpha",
        "bravo",
        "charlie",
        "delta",
        "echo",
        "golf",
        "hotel",
        "a1",
        "a2",
        "a3",
        "a4",
        "a5",
        "a6",
        "a7",
        "a8",
        "b1",
        "b2",
        "b3",
        "b4",
        "b5",
        "b6",
        "b7",
        "b8",
        "c1",
        "c2",
        "c3",
        "c4",
        "c5",
        "c6",
        "c7",
        "c8",
        "d1",
        "d2",
        "d3",
        "d4",
        "d5",
        "d6",
        "d7",
        "d8",
		"e1",
        "e2",
        "e3",
        "e4",
        "e5",
        "e6",
        "e7",
        "e8",
        "f1",
        "f2",
        "f3",
        "f4",
        "f5",
        "f6",
        "f7",
        "f8",
        "g1",
        "g2",
        "g3",
        "g4",
        "g5",
        "g6",
        "g7",
        "g8",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "h7",
        "h8",
        "quit",
        "exit"
        ]
FILE_MULTIPLIER = {
        'a': 0,
        'b': 1,
        'c': 2,
        'd': 3,
        'e': 4,
        'f': 5,
        'g': 6,
        'h': 7
        }
RANK_MULTIPLIER = {
        '1': 0,
        '2': 1,
        '3': 2,
        '4': 3,
        '5': 4,
        '6': 5,
        '7': 6,
        '8': 7
        }

class CDSService(object):
    """
    Service performs the following:
        - Polls the screen for a chess board
        - Listens for a text-based or mic-based chess move
        - Evaluates the starting and end positions of the chess move
        - Automates mouse movements of the chess move
    """
    def __init__(self):
        ## Logging
        logging.basicConfig(format='%(asctime)s %(message)s', 
                    datefmt='%m/%d/%Y %I:%M:%S %p')
        self.logger = logging.getLogger('CDSService')
        self.logger.setLevel(LOG_LEVEL)
        
        ## Chess logic
        self.chess_board = chess.Board()
        
        ## Board detection
        self.board_corners = [0, 0, 0, 0]
        self.predictor = tensorflow_chessbot.ChessboardPredictor(
                frozen_graph_path='chessfenbot/saved_models/frozen_graph.pb')
        
        ## Speech recognition
        self.recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            self.logger.info('Be quiet please... adjusting for ambient microphone noise (5s)...')
            self.recognizer.adjust_for_ambient_noise(source, duration=5)
            self.logger.info('Adjustment complete.')       
            
        ## GUI window
        self.window = self._init_gui_window()


    def _init_gui_window(self):
        """
        Initialize the tkinter window for the GUI
        """
        window = tkinter.Tk()
        
        tkinter.Label(window, text="== CHESS DICTATION SYSTEM ==").grid(row=0)
        
        tkinter.Label(window, text="Speech:").grid(row=1, column=0)
        self.speech_label = tkinter.StringVar(value="Press M to talk.")
        tkinter.Label(window, textvariable=self.speech_label).grid(row=1, column=1)
        
        tkinter.Label(window, text="Status:").grid(row=2, column=0)
        self.status_label = tkinter.StringVar(value="Started.")
        tkinter.Label(window, textvariable=self.status_label).grid(row=2, column=1)
            
        def key_up(keypress):
            self.logger.debug("key_up: " + keypress.char)
            if(keypress.char == "m"):
                self.get_command_from_speech()
            
        def polling_task():
            self.set_board_from_screen()
            window.after(1000, polling_task)
        
        window.bind("<KeyRelease>", key_up)
        window.lift()
        window.attributes("-topmost", True)
        window.after(0, polling_task)
        return window
    
    def _set_speech_label(self, message):
        """
        Displays a new string in the speech output in the GUI
        """
        self.speech_label.set(message)
        self.logger.info("Speech box change: " + message)
        
        
    def _set_status_label(self, message):
        """
        Displays a new string in the status output in the GUI
        """
        self.status_label.set(message)
        self.logger.info("Status box change: " + message)
    
    
    def _automate_move(self, starting_coord, ending_coord):
        """
        Activates mouse clicks for moving chess pieces
        """
        pyautogui.moveTo(starting_coord[0], starting_coord[1], duration=0.01)
        pyautogui.dragTo(ending_coord[0], ending_coord[1], duration=0.25)
        self.window.focus_force()
    
    
    def _square_to_coord(self, square):
        """
        Converts a square to a screen coordinate
        Assumes A1 is always bottom left
        """
        board_length = self.board_corners[2] - self.board_corners[0]
        board_height = self.board_corners[3] - self.board_corners[1]
        
        step_length = int(board_length / 8)
        step_height = int(board_height / 8)
        
        start_length = int(step_length / 2)
        start_height = int(step_height / 2)
        
        file_multiplier = FILE_MULTIPLIER[square[0]]
        rank_multiplier = RANK_MULTIPLIER[square[1]]
        
        coord = [self.board_corners[0] + start_length + (file_multiplier * step_length),
                 self.board_corners[3] - start_height - (rank_multiplier * step_height)]
        return coord
    

    def set_board_from_screen(self):
        """
        Set the instance chessboard if found on the screen.
        """
        self.logger.debug('START set_board_from_screen')
        screenshot = pyautogui.screenshot()
        tiles = None
        tiles, corners = chessboard_finder.findGrayscaleTilesInImage(screenshot)
        if(tiles is not None):
            fen, tile_certainties = self.predictor.getPrediction(tiles)
            fen = shortenFEN(fen)
            self.chess_board.set_board_fen(fen)
            self.board_corners = corners
            self.logger.info('SUCCESS Got board.')
            self.logger.debug('FEN is ' + fen)
            self.logger.debug('Corners are ' + str(corners))
            
            certainty = tile_certainties.min()
            self.logger.debug('Per-tile certainty:')
            self.logger.debug(tile_certainties)
            self.logger.debug("Certainty range [%g - %g], Avg: %g" % (
                    tile_certainties.min(), tile_certainties.max(), 
                    tile_certainties.mean()))
            self.logger.debug("Final Certainty: %.1f%%" % (certainty*100))
        else:
            self.logger.info('FAIL No tiles detected.')
        self.logger.debug('END set_board_from_screen')
    
    
    def try_san_move(self, move_string):
        """
        Attempts a standard notation string against the chessboard
        """
        self.logger.debug('START try_san_move')
        try:
            move = self.chess_board.parse_san(move_string)
            if(move in self.chess_board.legal_moves):
                self.logger.info("This move is legal")
                self._set_status_label("Moving " + chess.SQUARE_NAMES[move.from_square] +
                                   " to " + chess.SQUARE_NAMES[move.to_square])
                starting_coord = self._square_to_coord(chess.SQUARE_NAMES[move.from_square])
                ending_coord = self._square_to_coord(chess.SQUARE_NAMES[move.to_square])
                self._automate_move(starting_coord, ending_coord)
            else:
                self._set_status_label("Illegal move " + move_string)
                self.logger.warning("Illegal move " + move_string)
        except ValueError:
            self._set_status_label("Invalid move " + move_string)
            self.logger.warning("Invalid move " + move_string)
        self.logger.debug('END try_san_move')
        

    def get_command_from_speech(self):
        """
        Listen to the microphone and get a SAN move from speech.
        """
        with sr.Microphone() as source: 
            self._set_speech_label("Listening... speak now!")
            audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=2)
        try:
            speech_string = self.recognizer.recognize_google_cloud(
                    audio_data=audio,
                    credentials_json=None,
                    language=GCP_SPEECH_LANGUAGE,
                    preferred_phrases=SPEECH_API_PHRASES,
                    show_all=False)
            self._set_speech_label("Google heard '" + speech_string + "'")
            speech_command = self.parse_speech_command(speech_string)
            self.logger.info("Translated to command: '" + speech_command + "'")
            if speech_command in ["quit", "exit"]:
                self.logger.info("Closing due to voice command.")
                self.window.destroy()
            elif "black" in speech_command:
                self.chess_board.turn = chess.BLACK
                speech_command = speech_command.replace("black", "")
                self.try_san_move(speech_command)
            elif "white" in speech_command:
                self.chess_board.turn = chess.WHITE
                speech_command = speech_command.replace("white", "")
                self.try_san_move(speech_command)
            else:
                self.try_san_move(speech_command)
        except sr.UnknownValueError:  
            self._set_speech_label("Failed to understand audio.")
        except sr.RequestError as e:  
            print("Google error; {0}".format(e))
            
            
    def parse_speech_command(self, speech_string):
        """
        Parse the detected speech string into a command
        """
        speech_string = speech_string.lower()
        
        ## Change chess words to SAN notation
        word_dict = {
                "zero":     "0",
                "one":      "1",
                "two":      "2",
                "three":    "3",
                "four":     "4",
                "for":      "4",
                "five":     "5",
                "six":      "6",
                "seven":    "7",
                "eight":    "8",
                "nine":     "9",
                "alpha":    "a",
                "alfa":     "a",
                "bravo":    "b",
                "be":       "b",
                "charlie":  "c",
                "see":      "c",
                "delta":    "d",
                "echo":     "e",
                "foxtrot":  "f",
                "golf":     "g",
                "call":     "g",
                "hotel":    "h",
                "rook":     "R",
                "rock":     "R",
                "truck":    "R",
                "knight":   "N",
                "night":    "N",
                "bishop":   "B",
                "ship":     "B",
                "queen":    "Q",
                "king":     "K",
                " capture ":"",
                " captures ":"",
                " takes ":    "",
                " take ":    "",
                "pawn":    "",
                " the ":      "",
                " to ":       "",
                "echo.for":     "e4"
                }
        for key, value in word_dict.items():
            speech_string = speech_string.replace(key,value)
        
        ## Remove any spaces
        speech_string = speech_string.replace(" ","")
        
        return speech_string
    
        
def main():
    cds_service = CDSService()
    cds_service.window.mainloop()
    
    
if __name__ == "__main__":
    main()
    
