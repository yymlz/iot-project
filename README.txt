
IoT Project
===========

Overview
--------
This project implements a basic IoT telemetry system in Python. It allows sensors to send data to a central server over UDP, demonstrating simple device-to-server communication for collecting sensor readings.

Main files:

Main files:
- `src/server.py`: Server to receive data
- `src/client.py`: Sensor client
- `src/protocol.py`: Protocol logic

To run: Start the server, then run the client from the `src/` folder.

HOW TO RUN LOCALLY
------------------

1. Start the server (collector):

   cd src
   python3 server.py

   The server will listen on 127.0.0.1:5000


2. In a separate terminal, start the client (sensor):

   cd src
   python3 client.py

   Default parameters:
   - Device ID: 1001
   - Reporting interval: 1 second
   - Duration: 60 seconds


3. Custom parameters:

   python3 client.py <device_id> <interval> <duration>

   Example (Device 2001, every 5 seconds, for 30 seconds):
   python3 client.py 2001 5 30


4. Stop the server:
   Press Ctrl+C


BASELINE TEST SCRIPT
--------------------

   run_baseline_test.py
   with same instructions:{
      cd tests
      python run_baseline_test.py
   }
   -seeing all server receiving packets at server_log.txt

===========================================================================================
