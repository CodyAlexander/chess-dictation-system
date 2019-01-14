# -*- coding: utf-8 -*-
"""
@author: Cody Alexander

Python service, polls the screen to determine FEN of any detected
chess boards.

Changelog:
    2019-01-12 Cody Alexander - Created

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
        self.logger.setLevel(logging.DEBUG)
        
        ## Chess logic
        self.chess_board = chess.Board()
        
        ## Board detection
        self.board_corners = [0, 0, 0, 0]
        self.predictor = tensorflow_chessbot.ChessboardPredictor(
                frozen_graph_path='chessfenbot/saved_models/frozen_graph.pb')
        
        ## Speech recognition
        self.recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            self.logger.info('Be quiet... adjusting for ambient microphone noise (5s)...')
            self.recognizer.adjust_for_ambient_noise(source, duration=5)
            self.logger.info('Adjustment complete.')       
            
        ## GUI window
        self.window = self._init_gui_window()


    def _init_gui_window(self):
        """
        Initialize the tkinter window for the GUI
        """
        window = tkinter.Tk()
        
        tkinter.Label(window, text="Command").grid(row=0)
        
        command_input = tkinter.Entry(window)
        command_input.grid(row=0, column=1)
        
        def color_button():
            self.chess_board.turn = chess.BLACK
            
        def submit_button():
            self.try_san_move(command_input.get())
            
        def mic_button():
            self.get_move_from_speech()
            
        def key_up(key):
            print("key_up: " + str(key))
            
        def key_down(key):
            print("key_down: " + str(key))
            
        def polling_task():
            # Poll the screen for chessboard every second
            self.set_board_from_screen()
            self.set_turn_from_screen()
            window.after(1000, polling_task)
            
        tkinter.Button(window, text='Black Move', command=color_button).grid(row=3, 
                      column=0, sticky=tkinter.W, pady=4)
        tkinter.Button(window, text='Submit', command=submit_button).grid(row=3, 
                      column=1, sticky=tkinter.W, pady=4)
        tkinter.Button(window, text='Mic', command=mic_button).grid(row=3, 
                      column=2, sticky=tkinter.W, pady=4)
        
        window.bind("<KeyPress>", key_down)
        window.bind("<KeyRelease>", key_up)
        window.lift()
        window.attributes("-topmost", True)
        window.after(0, polling_task)
        return window
    
    
    def _automate_move(self, starting_coord, ending_coord):
        """
        Activates mouse clicks for moving chess pieces
        """
        pyautogui.moveTo(starting_coord[0], starting_coord[1], duration=0.01)
        pyautogui.dragTo(ending_coord[0], ending_coord[1], duration=0.25)
    
    
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
        
        
    def set_turn_from_screen(self):
        """
        Set the colour pieces that have next turn if found on the screen.
        """
        return True
    
    
    def try_san_move(self, move_string):
        """
        Attempts a standard notation string against the chessboard
        """
        self.logger.debug('START try_san_move')
        try:
            move = self.chess_board.parse_san(move_string)
            if(move in self.chess_board.legal_moves):
                self.logger.info("This move is legal")
                starting_coord = self._square_to_coord(chess.SQUARE_NAMES[move.from_square])
                ending_coord = self._square_to_coord(chess.SQUARE_NAMES[move.to_square])
                self._automate_move(starting_coord, ending_coord)
            else:
                self.logger.warning("This move is not legal")
        except ValueError:
            self.logger.warning("Invalid move")
        
        self.logger.debug('START try_san_move')
        
        
    def get_move_from_speech(self):
        """
        Listen to the microphone and get a SAN move from speech.
        """
        with sr.Microphone() as source: 
            audio = self.recognizer.listen(source)
        try:
            print("Sphinx thinks you said '" + 
                  self.recognizer.recognize_sphinx(audio) + "'")  
        except sr.UnknownValueError:  
            print("Sphinx could not understand audio")  
        except sr.RequestError as e:  
            print("Sphinx error; {0}".format(e))
    
        
def main():
    cds_service = CDSService()
    cds_service.window.mainloop()
    
    
if __name__ == "__main__":
    main()
    
