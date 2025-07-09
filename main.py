#!/usr/bin/env python3
"""
Enhanced CD Player - Main Entry Point
"""
import os
import signal
import sys
from cd.cd_player import CDPlayer

def signal_handler(signum, frame):
    print("\n👋 Shutting down...")
    if 'player' in globals():
        player.shutdown()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    player = CDPlayer()
    player.run()

if __name__ == '__main__':
    main()
