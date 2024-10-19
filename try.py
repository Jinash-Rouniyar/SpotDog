import os
import time
import subprocess
import tempfile
from spot_controller import SpotController
import cv2
from math_bot import math_chain, question, answer_exp
import azure.cognitiveservices.speech as speechsdk
from azure_pronunciation import SpeechToTextManager
import requests

ROBOT_IP = "192.168.80.3"
SPOT_USERNAME = "admin"
SPOT_PASSWORD = "2zqa8dgw7lor"
WAVE_OUTPUT_FILENAME = "aaaa.wav"
LANG_CODE = "en-US"

class RoomExplorationBot:
    def __init__(self, spot_username, spot_password, robot_ip):
        # Initialize Spot controller parameters
        self.spot_username = spot_username
        self.spot_password = spot_password
        self.robot_ip = robot_ip
        
        # Initialize speech components
        self.speech_config = speechsdk.SpeechConfig(
            subscription=os.environ.get('SPEECH_KEY'), 
            region=os.environ.get('SPEECH_REGION')
        )
        self.speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=self.speech_config)
        self.speech_to_text_manager = SpeechToTextManager()
        
        # Initialize object detection list
        self.detected_objects = []
        
    def detect_objects(self, image):
        """
        Detect objects in the captured image using OpenCV.
        Returns list of detected objects with their positions.
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        params = cv2.SimpleBlobDetector_Params()
        params.minThreshold = 10
        params.maxThreshold = 200
        params.filterByArea = True
        params.minArea = 1500
        
        detector = cv2.SimpleBlobDetector_create(params)
        keypoints = detector.detect(gray)
        
        # Store detected objects with their locations
        objects = [(int(k.pt[0]), int(k.pt[1])) for k in keypoints]
        self.detected_objects.extend(objects)
        
        return keypoints

    def inspect_object(self, spot, sleep_time=1):
        """
        Perform an inspection motion (head nod) when examining an object.
        """
        try:
            # Nod down to inspect
            spot.move_head_in_points(
                yaws=[0],
                pitches=[0.5],  # Look down
                rolls=[0],
                sleep_after_point_reached=sleep_time
            )
            
            # Capture image while looking down
            self.capture_image()
            
            # Return to original position
            spot.move_head_in_points(
                yaws=[0],
                pitches=[0],
                rolls=[0],
                sleep_after_point_reached=sleep_time
            )
        except Exception as e:
            print(f"Error during object inspection: {e}")
            spot.move_head_in_points(yaws=[0], pitches=[0], rolls=[0])

    def capture_image(self):
        camera_capture = cv2.VideoCapture(0)
        rv, image = camera_capture.read()
        camera_capture.release()
        return rv, image

    def capture_and_process(self, spot, capture_interval=2):
        rv, image = self.capture_image()
        
        if rv:
            objects = self.detect_objects(image)
            if objects:
                print(f"Detected {len(objects)} objects - initiating inspection")
                self.inspect_object(spot)
            
            cv2.imwrite(f"exploration_frame_{time.time()}.jpg", image)
        
        time.sleep(capture_interval)

    def explore_room(self, spot, capture_interval=2):
        """
        Execute room exploration pattern with object detection.
        """
        print("Starting room exploration...")
        
        try:
            # 1. Enter room
            print("Phase 1: Entering room...")
            spot.move_to_goal(goal_x=1.5, goal_y=0)
            self.capture_and_process(spot, capture_interval)
            
            # 2. Scan the room from entrance
            print("Phase 2: Initial room scan...")
            scan_positions = [
                (0.4, 0.3, 0),   # Look right-up
                (0, 0.3, 0),     # Look up
                (-0.4, 0.3, 0),  # Look left-up
                (-0.4, 0, 0),    # Look left
                (0, 0, 0),       # Look center
                (0.4, 0, 0),     # Look right
            ]
            
            for yaw, pitch, roll in scan_positions:
                spot.move_head_in_points(
                    yaws=[yaw],
                    pitches=[pitch],
                    rolls=[roll],
                    sleep_after_point_reached=1
                )
                self.capture_and_process(spot, capture_interval)
                
            # 3. Move in a square pattern
            print("Phase 3: Room exploration pattern...")
            movements = [
                (0, 1),    # Move left 1m
                (1, 0),    # Move forward 1m
                (0, -1),   # Move right 1m
                (-1, 0),   # Move back 1m
            ]
            
            for dx, dy in movements:
                spot.move_to_goal(goal_x=dx, goal_y=dy)
                for yaw, pitch, roll in [(0.3, 0.2, 0), (0, 0.2, 0), (-0.3, 0.2, 0)]:
                    spot.move_head_in_points(
                        yaws=[yaw],
                        pitches=[pitch],
                        rolls=[roll],
                        sleep_after_point_reached=1
                    )
                    self.capture_and_process(spot, capture_interval)
            
            # 4. Return to start
            print("Phase 4: Returning to start position...")
            spot.move_to_goal(goal_x=-1.5, goal_y=0)
            spot.move_head_in_points(yaws=[0], pitches=[0], rolls=[0], sleep_after_point_reached=1)
            
        except Exception as e:
            print(f"Error during room exploration: {e}")
            spot.move_head_in_points(yaws=[0], pitches=[0], rolls=[0])
            raise
        
        return len(self.detected_objects)

    def stream_and_synthesize_response(self, text):
        """
        Stream and synthesize speech response.
        """
        with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as temp_audio_file:
            ffplay_process = subprocess.Popen(
                ['ffplay', 
                 '-f', 's16le',
                 '-ar', '16000',
                 '-ac', '1',
                 '-i', 'pipe:0',
                 '-nodisp',
                 '-autoexit'
                ],
                stdin=subprocess.PIPE,
                bufsize=0
            )

            result = self.speech_synthesizer.speak_text_async(text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                try:
                    ffplay_process.stdin.write(result.audio_data)
                    ffplay_process.stdin.flush()
                except BrokenPipeError:
                    print("Audio stream was closed")
            else:
                print(f"Speech synthesis failed: {result.reason}")

            try:
                ffplay_process.stdin.close()
            except:
                pass
            ffplay_process.wait()

    def run(self):
        """
        Main run loop that handles the entire interaction.
        """
        # Record audio input
        print("Start recording audio")
        cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 aaaa.wav'
        os.system(cmd)
        print("Audio recording completed")

        # Transcribe the recorded audio
        user_input = self.speech_to_text_manager.speechtotext_from_file("aaaa.wav", "en-US")
        print(f"Transcribed user input: {user_input}")

        # Initialize Spot and perform exploration
        with SpotController(
            username=self.spot_username, 
            password=self.spot_password, 
            robot_ip=self.robot_ip
        ) as spot:
            num_objects = self.explore_room(spot)
            
            # Generate response based on exploration results
            response = f"I have completed the room exploration. I detected {num_objects} objects "
            if num_objects > 0:
                response += "and performed detailed inspections of each object. "
            else:
                response += "but did not find any items requiring detailed inspection. "
            response += "I have now returned to my starting position."
            
            # Synthesize and play the response
            self.stream_and_synthesize_response(response)

def main():
    bot = RoomExplorationBot(
        spot_username=SPOT_USERNAME,
        spot_password=SPOT_PASSWORD,
        robot_ip=ROBOT_IP
    )
    bot.run()

if __name__ == "__main__":
    main()