#===========================================
# VQH: Variational Quantum Harmonizer
# Sonification of the VQE Algorithm
# Authors: Paulo Itaborai, Tim Schwägerl,
# María Aguado Yáñez, Arianna Crippa
#
# ICCMR, University of Plymouth, UK
# CQTA, DESY Zeuthen, Germany
# Universitat Pompeu Fabra, Spain
#
# Jan 2023 - Jan 2024
#===========================================


# Logging and global variables
import logging
import sys
import time

# Global variables
import config

from core.vqh_core_old import VQH
from core.vqh_core_new import VQHCore, VQHController

# Event Management
import json
from csv import DictReader
import os
from collections import deque

# CLI Interface
import argparse
from argparse import RawDescriptionHelpFormatter
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator
import multiprocessing
import threading

from control_to_setup2 import json_to_csv

level = logging.DEBUG

fmt = logging.Formatter('[%(levelname)s]:%(name)s - %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(fmt)
logger = logging.getLogger(__name__)
logger.setLevel(level)
logger.addHandler(handler)

global progQuit
progQuit = False
comp = True
last = False
reset = True
port = ''

VALID_COMMANDS = ['play', 'runvqe', 'q', 'quit', 'stop', 'playfile', 'map', 'mapfile', 'realtime', 'rt']


# Play sonification from a previously generated file
def playfile(num, folder, son_type=1):
    path = f"{folder}/Data_{num}"
    with open(f"{path}/aggregate_data.json") as afile:
        dist = json.load(afile)
    with open(f"{path}/exp_values.txt") as efile:
        vals = [float(val.rstrip()) for val in efile]
    sc.sonify(dist, vals, son_type)



def is_command(cmd):
    return cmd.split(' ')[0] in VALID_COMMANDS
    
def update_qubo_visualization(pquit):
    while not pquit.value:
        try:
            json_to_csv('midi/qubo_control.json', 'output.csv')
            time.sleep(0.1)
        except Exception:
            continue

# Function to print all currently running threads
def list_active_threads():
    for thread in threading.enumerate():
        print(f"Thread Name: {thread.name}, Alive: {thread.is_alive()}")


def CLI(vqh, vqh_core, vqh_controller):
    global progQuit, comp, last, reset, generated_quasi_dist, comp_events
    generated_quasi_dist = []
    

    # prompt preparation
    session = PromptSession()
    validator = Validator.from_callable(is_command, error_message='This command does not exist. Check for mispellings.')

    while not progQuit:
        try:
      
            #CLI Commands
            x = session.prompt(f' VQH=> ', validator=validator, validate_while_typing=False)
            x = x.split(' ')
            if x[0] == 'next' or x[0] == 'n':
                print(f'Score Features not implemented yet for the VQH!')


            elif x[0] == 'quit' or x[0] == 'q':
                progQuit=True
                continue

            
            # Main VQH Command
            elif x[0] == 'runvqe':
                if len(x) == 1:
                    print("running VQE")
                    #generated_quasi_dist, generated_values = vqh.run_vqh(globalsvqh.SESSIONPATH)
                    vqh.runvqe(config.SESSIONPATH)
                else:
                    print('Error! Try Again')
            
            # Sonify From a previously generated VQE result in the session folder
            elif x[0] == 'playfile':
                son_type = 1
                if len(x) == 3:
                    son_type = int(x[2])
                #playfile(x[1], config.SESSIONPATH, son_type)
                vqh.playfile(x[1], config.SESSIONPATH, son_type)
            
            # Same as using ctrl+. in SuperCollider
            elif x[0] == 'stop':
                #sc.freeall()
                vqh.stop_sc_sound()
            
            # Sonify the last generated VQE result
            elif x[0] == 'play':
                if generated_quasi_dist != []:
                    son_type = 1
                    if len(x) == 2:
                        son_type = int(x[1])
                    #sc.sonify(generated_quasi_dist, generated_values, son_type)
                    vqh.play(son_type)
                else:
                    print("Quasi Dists NOT generated!")

            elif x[0] == 'map':
                if vqh.data:
                    son_type = 1
                    if len(x) == 2:
                        son_type = int(x[1])
                    #sc.sonify(generated_quasi_dist, generated_values, son_type)
                    vqh.map_sonification(son_type)
                    
                else:
                    print("Quasi Dists NOT generated!")
            elif x[0] == 'mapfile':
                son_type = 1
                if len(x) == 3:
                    son_type = int(x[2])
                #playfile(x[1], config.SESSIONPATH, son_type)
                vqh.mapfile(x[1], config.SESSIONPATH, son_type)


            elif x[0] == 'realtime' or x[0] == 'rt':
                print('')
                vqh_controller.start()

            else:
                print(f'Not a valid input - {x}')

        except KeyboardInterrupt:

            print('Keyboard Interrupt!')
            try:
                vqh_controller.clean()
            except Exception:
                pass
            progQuit = True
            print('Exiting VQH...')
            time.sleep(1)
            print('Goodbye!')
            

if __name__ == '__main__':


    descr = 'Variational Quantum Harmonizer\n\
CSV QUBOS syntax and rules:\n\
- File name MUST BE "h_setup.csv"\n\
- QUBO matrices should be exactly as the one below.\n\
The header should contain the matrix name and note labels.\n\
NO SPACE between commas for header and labels!\n\
Spaces allowed only for number entries. See "h_setup-Example.csv"\n\
    h1,label1,label2,label3,...,labeln\n\
    label1,c11,c12,c13,...,c1n\n\
    label2,c21,c22,c23,...,c2n\n\
    label3,c31,c32,c33,...,c3n\n\
    ...\n\
    labeln,cn1,cn2,cn3,...,cnn\n\
    h2,label1,label2,label3,...,labeln\n\
    label1,c11,c12,c13,...,c1n\n\
    ... \n\n\
Internal VQH functions:\n\
=> runvqe               Runs VQE and extracts sonification parameters.\n\
=> play                 Triggers a sonification method using the current\n\
                        VQE data extracted from the last call of "runvqe".\n\
                        The first argument is the sonification method.\n\
=> playfile             Triggers a sonification method using data stores in \n\
                        the session folder. The file index is the first \n\
                        argument. The second argument is the sonification \n\
=> stop                 Stops all sound in SuperCollider.\n\
=> quit, q              Exits the program.\n '


    p = argparse.ArgumentParser(description=descr, formatter_class=RawDescriptionHelpFormatter)

    p.add_argument('sessionpath', type=str, nargs='?', default='Session', help="Folder name where VQE data will be stored/read")
    p.add_argument('platform', type=str, nargs='?', default='local', help="Quantum Platform provider used (Local, IQM, IBMQ). Default is 'local'.")
    p.add_argument('protocol', type=str, nargs='?', default='harp', help="Encoding strategy for generating sonification data. Default is 'harp'.")
    p.add_argument('process', type=str, nargs='?', default='test', help="Process to be sonified. Default is 'test'.")
    p.add_argument('process_mode', type=str, nargs='?', default='fixed', help="Process mode. Default is 'fixed'.")
    p.add_argument('rt_son', type=int, nargs='?', default=9, help="Real-time sonification method. Default is 9.")
    args = p.parse_args()
    logger.debug(args)


    config.SESSIONPATH = args.sessionpath
    config.HW_INTERFACE = args.platform

    vqh = VQH(args.protocol, args.platform)
    vqh_core = VQHCore('process', args.process, args.platform, args.rt_son, args.process_mode)
    vqh_controlller = VQHController(vqh_core)


    print('=====================================================')
    print('      VQH: Variational Quantum Harmonizer  - v0.3    ') 
    print('          by itaborala, schwaeti, maria-aguado,      ')
    print('               cephasteom, ariannacrippa           ')
    print('                     2023 - 2024                     ') 
    print('                     DESY + ICCMR                    ')
    print('              karljansen  + iccmr-quantum            ')
    print('         https://github.com/iccmr-quantum/VQH        ')
    print('=====================================================')

    # Run CLI
    pquit = multiprocessing.Value('b', False)
    qubo_vis = multiprocessing.Process(target=update_qubo_visualization, args=(pquit,))
    qubo_vis.start()

    CLI(vqh, vqh_core, vqh_controlller)
    pquit.value = True
    print('Exited VQH')
    list_active_threads()
