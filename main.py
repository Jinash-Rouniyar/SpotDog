import cv2
import numpy as np
from collections import deque
from dataclasses import dataclass
from spot_controller import SpotController
from typing import List, Tuple
from bosdyn.client import create_standard_sdk
from bosdyn.client.robot import Robot
from bosdyn.client.image import ImageClient
from bosdyn.api import image_pb2
import time
import os
import math
from deepgram import Deepgram
from groq_bot import groq_chain
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import keyboard

@dataclass
class LED:
    position: Tuple[int, int]
    radius: int
    last_seen: int

class SpotThreatDetector:
    def __init__(self, spot_controller):
        self.spot_controller = spot_controller
        self.image_client = self.spot_controller.robot.ensure_client(ImageClient.default_service_name)
        
        # Initialize threat detection parameters
        self.led_history = deque(maxlen=10)
        self.frame_count = 0
        self.led_tracker = []
        
        # Available camera sources
        self.camera_sources = [
            "frontleft_fisheye_image",
            "frontright_fisheye_image",
            "left_fisheye_image",
            "right_fisheye_image",
            "back_fisheye_image"
        ]
        self.current_camera = self.camera_sources[0]
    
    def capture_frame(self):
        """Captures a frame from Spot's current camera"""
        try:
            image_responses = self.image_client.get_image_from_sources([self.current_camera])
            if not image_responses:
                raise Exception("No image responses received")
            
            image_response = image_responses[0]
            image_data = image_response.shot.image.data
            
            # Convert to OpenCV format
            numpy_array = np.frombuffer(image_data, dtype=np.uint8)
            frame = cv2.imdecode(numpy_array, cv2.IMREAD_COLOR)
            
            if frame is None:
                raise Exception("Failed to decode image data")
                
            return frame
            
        except Exception as e:
            print(f"Error capturing frame: {str(e)}")
            return None
    
    def process_frame(self, frame):
        """Process frame for threat detection"""
        if frame is None:
            return None, False
            
        # Convert to HSV for better red detection
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Define range for red color
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        # Create masks for red detection
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # Apply noise reduction
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        
        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        current_leds = []
        for contour in contours:
            if cv2.contourArea(contour) > 50:
                ((x, y), radius) = cv2.minEnclosingCircle(contour)
                if radius > 5:
                    current_leds.append(LED((int(x), int(y)), int(radius), self.frame_count))
        
        self.led_history.append(current_leds)
        return self.detect_threat(frame)
    
    def detect_threat(self, frame):
        """Detect potential threats in the frame"""
        if len(self.led_history) < 5:
            return frame, False
            
        led_groups = []
        for leds in self.led_history:
            if len(leds) >= 3:
                positions = [(led.position[0], led.position[1]) for led in leds]
                led_groups.append(positions)
        
        if len(led_groups) < 5:
            return frame, False
            
        threat_detected = False
        threat_box = None
        
        for i in range(len(led_groups[-1])):
            nearby_leds = []
            center = led_groups[-1][i]
            
            for j in range(len(led_groups[-1])):
                if i != j:
                    dx = center[0] - led_groups[-1][j][0]
                    dy = center[1] - led_groups[-1][j][1]
                    distance = np.sqrt(dx*dx + dy*dy)
                    if distance < 100:
                        nearby_leds.append(led_groups[-1][j])
            
            if len(nearby_leds) >= 2:
                threat_detected = True
                all_points = [center] + nearby_leds
                min_x = min(p[0] for p in all_points)
                min_y = min(p[1] for p in all_points)
                max_x = max(p[0] for p in all_points)
                max_y = max(p[1] for p in all_points)
                
                padding = 20
                threat_box = (
                    max(0, min_x - padding),
                    max(0, min_y - padding),
                    min(frame.shape[1], max_x + padding),
                    min(frame.shape[0], max_y + padding)
                )
                break
        
        if threat_detected and threat_box:
            cv2.rectangle(frame, 
                        (int(threat_box[0]), int(threat_box[1])),
                        (int(threat_box[2]), int(threat_box[3])),
                        (0, 0, 255), 2)
            cv2.putText(frame, "THREAT DETECTED", 
                       (int(threat_box[0]), int(threat_box[1] - 10)),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            
            # Save frame when threat is detected
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            cv2.imwrite(f"threat_detected_{timestamp}.jpg", frame)
        
        return frame, threat_detected
    
    def create_thermal_vision(self, frame):
        """Create thermal vision effect from regular frame"""
        if frame is None:
            return None
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(blurred)
        thermal = cv2.applyColorMap(enhanced, cv2.COLORMAP_JET)
        thermal = cv2.addWeighted(thermal, 1.2, thermal, 0, 0)
        return thermal
    
    def switch_camera(self):
        """Switch to next available camera"""
        current_index = self.camera_sources.index(self.current_camera)
        next_index = (current_index + 1) % len(self.camera_sources)
        self.current_camera = self.camera_sources[next_index]
        print(f"Switched to camera: {self.current_camera}")
    
    def capture_head_movement_frames(self, start_pitch, end_pitch, num_frames):
        """Capture frames as the robot moves its head down"""
        frames_dir = 'head_movement_frames'
        os.makedirs(frames_dir, exist_ok=True)

        pitch_step = (end_pitch - start_pitch) / (num_frames - 1)
        pitches = [start_pitch + i * pitch_step for i in range(num_frames)]

        for _ in self.spot_controller.move_head_in_points(yaws=[0]*num_frames, pitches=pitches, rolls=[0]*num_frames, sleep_after_point_reached=0.1):
            # Capture frame
            frame = self.capture_frame()
            if frame is not None:
                # Process frame
                processed_frame, threat_detected = self.process_frame(frame.copy())
                thermal_frame = self.create_thermal_vision(frame)
                
                # Save frames
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                frame_number = f"{self.frame_count:04d}"
                
                cv2.imwrite(os.path.join(frames_dir, f'original_{timestamp}_{frame_number}.jpg'), frame)
                if processed_frame is not None:
                    cv2.imwrite(os.path.join(frames_dir, f'threat_detection_{timestamp}_{frame_number}.jpg'), processed_frame)
                if thermal_frame is not None:
                    cv2.imwrite(os.path.join(frames_dir, f'thermal_vision_{timestamp}_{frame_number}.jpg'), thermal_frame)
                
                self.frame_count += 1

        print(f"Captured {self.frame_count} frames during head movement. Saved in '{frames_dir}' directory.")

    def run_head_movement_capture(self):
        """Run the head movement capture sequence"""
        # Move head down and capture frames
        self.capture_head_movement_frames(start_pitch=0, end_pitch=0.5, num_frames=20)
        
        # Move head back to normal position
        self.spot_controller.move_head_in_points(yaws=[0], pitches=[0], rolls=[0], sleep_after_point_reached=1)

    def execute_smooth_u_turn(self, turn_radius=0.3):
        """
        Performs a faster, tighter smooth 360-degree turn with the Spot robot
        """
        # Angular velocity (rad/s) - faster rotation
        v_rot = 0.8
        # Linear velocity (m/s) - move in a smaller circle
        v_x = turn_radius * v_rot

        # Calculate time for a full 360-degree turn
        turn_time = (2 * math.pi / v_rot) * 1.1

        # Number of segments for the turn
        num_segments = 20
        segment_time = turn_time / num_segments

        # Execute the turn in segments
        for i in range(num_segments):
            # Calculate current angle in the turn
            angle = (i / num_segments) * 2 * math.pi
            
            # Calculate velocities for circular motion
            current_v_x = v_x * math.cos(angle)
            current_v_y = v_x * math.sin(angle)
            
            self.spot_controller.move_by_velocity_control(
                v_x=current_v_x,
                v_y=current_v_y,
                v_rot=v_rot,
                cmd_duration=segment_time
            )
            time.sleep(segment_time)

        # Brief pause to stabilize
        time.sleep(0.5)

    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file using Deepgram API"""
        DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')
        
        if not DEEPGRAM_API_KEY:
            print("Error: DEEPGRAM_API_KEY not found in environment variables.")
            return None

        dg_client = Deepgram(DEEPGRAM_API_KEY)

        with open(audio_file_path, 'rb') as audio:
            source = {'buffer': audio, 'mimetype': 'audio/wav'}
            options = {"punctuate": True, "model": "general", "language": "en-US"}

            try:
                response = dg_client.transcription.sync_prerecorded(source, options)
                transcript = response["results"]["channels"][0]["alternatives"][0]["transcript"]
                return transcript
            except Exception as e:
                print(f"Error during transcription: {str(e)}")
                return None
    def execute_direction(self,instruction):
        if instruction == "quit":
            print("Quitting continuous control mode.")

        elif instruction == "up":
            self.spot_controller.move_to_goal(goal_x=1.0, goal_y=0)
            print("Moving forward 1 meter")

        elif instruction == "down":
            self.spot_controller.move_to_goal(goal_x=-1.0, goal_y=0)
            print("Moving backward 1 meter")

        elif instruction == "left":
            print("Turning left and moving forward")
            self.spot_controller.move_head_in_points(yaws=[0.5], pitches=[0], rolls=[0])
            time.sleep(0.5)  # Wait for head movement to complete
            self.spot_controller.move_to_goal(goal_x=1.0, goal_y=0)
            self.spot_controller.move_head_in_points(yaws=[0], pitches=[0], rolls=[0])  # Reset head position

        elif instruction == "right":
            print("Turning right and moving forward")
            self.spot_controller.move_head_in_points(yaws=[-0.5], pitches=[0], rolls=[0])
            time.sleep(0.5)  # Wait for head movement to complete
            self.spot_controller.move_to_goal(goal_x=1.0, goal_y=0)
            self.spot_controller.move_head_in_points(yaws=[0], pitches=[0], rolls=[0])  # Reset head position

        elif instruction == "turn":
            print("Executing smooth 360-degree turn")
            self.execute_smooth_u_turn()

        elif instruction == "scan":
            print("Moving head down and capturing frames")
            self.run_head_movement_capture()

        # Add a small delay to prevent excessive CPU usage
        time.sleep(0.1)
    def run_complete_sequence(self):
        audio_file_path = "initial_recording.wav"
        
        transcript = self.transcribe_audio(audio_file_path)
        cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 {audio_file_path}'
        print(cmd)
        os.system(cmd)
        if transcript:
            print("Audio Transcript:")
            print(transcript)
        else:
            print("Failed to transcribe audio.")
        
        response = groq_chain.invoke({"question": transcript})
        print(response)

        for instruction in response:
            self.execute_direction(instruction)
        
        # self.spot_controller.move_to_goal(goal_x=2.5, goal_y=0) 
        # time.sleep(2)
        # self.spot_controller.move_head_in_points(yaws=[0.2], pitches=[0], rolls=[0], sleep_after_point_reached=1)

        # self.run_head_movement_capture()
        # self.spot_controller.move_head_in_points(yaws=[0], pitches=[0], rolls=[0], sleep_after_point_reached=1)
        # self.spot_controller.move_to_goal(goal_x=1.5, goal_y=0)  
        # time.sleep(2)
        # self.spot_controller.move_head_in_points(yaws=[-0.2], pitches=[0], rolls=[0], sleep_after_point_reached=1)
        # self.run_head_movement_capture()
        # self.spot_controller.move_head_in_points(yaws=[0], pitches=[0], rolls=[0], sleep_after_point_reached=1)
        
        # time.sleep(2)
        # print("Executing smooth U-turn")
        # self.run_head_movement_capture()
        # time.sleep(2)
        # self.execute_smooth_u_turn(forward_distance=2.5, turn_radius=0.5)
        # time.sleep(5)
        
def main():
    # Replace these with your Spot robot's credentials
    ROBOT_IP = "192.168.80.3"
    SPOT_USERNAME = "admin"
    SPOT_PASSWORD = "2zqa8dgw7lor"
    
    # Initialize SpotController
    with SpotController(username=SPOT_USERNAME, password=SPOT_PASSWORD, robot_ip=ROBOT_IP) as spot:
        # Initialize SpotThreatDetector with SpotController
        detector = SpotThreatDetector(spot)
        
        # Run the complete sequence
        detector.run_complete_sequence()

if __name__ == "__main__":
    main()
