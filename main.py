import os
import time
import base64
from spot_controller import SpotController
import cv2
from math_bot import math_chain, question, answer_exp
import azure.cognitiveservices.speech as speechsdk
from azure_pronunciation import SpeechToTextManager

ROBOT_IP = "192.168.80.3"#os.environ['ROBOT_IP']
SPOT_USERNAME = "admin"#os.environ['SPOT_USERNAME']
SPOT_PASSWORD = "2zqa8dgw7lor"#os.environ['SPOT_PASSWORD']
WAVE_OUTPUT_FILENAME = "aaaa.wav"
LANG_CODE = "en-US"  # Adjust this if needed

# Initialize Azure Speech SDK
speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

# Initialize SpeechToTextManager
speech_to_text_manager = SpeechToTextManager()

def capture_image():
    camera_capture = cv2.VideoCapture(0)
    rv, image = camera_capture.read()
    print(f"Image Dimensions: {image.shape}")
    camera_capture.release()

def stream_and_synthesize_response(user_input):
    def stream_output():
        buffer = ""
        for chunk in math_chain.stream({
            "question": question,
            "answer_exp": answer_exp,
            "student_input": user_input
        }):
            buffer += chunk
            if len(buffer) >= 50 or '.' in buffer or '?' in buffer:
                yield buffer
                buffer = ""
        if buffer:
            yield buffer

    full_response = ""
    for text_chunk in stream_output():
        full_response += text_chunk
        
        # Generate speech from the text chunk
        result = speech_synthesizer.speak_text_async(text_chunk).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            # Convert audio data to base64
            audio_base64 = base64.b64encode(result.audio_data).decode('utf-8')
            
            # Here you would typically emit or send the audio data
            # For this example, we'll just print it
            print(f"Text chunk: {text_chunk}")
            print(f"Audio data (base64): {audio_base64[:50]}...")  # Print first 50 chars
        else:
            print(f"Speech synthesis failed: {result.reason}")

    return full_response

def main():
    print("Start recording audio")
    cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 {WAVE_OUTPUT_FILENAME}'
    print(cmd)
    os.system(cmd)
    print("Audio recording completed")

    # Transcribe the recorded audio
    user_input = speech_to_text_manager.speechtotext_from_file(WAVE_OUTPUT_FILENAME, LANG_CODE)
    print(f"Transcribed user input: {user_input}")

    # Stream and synthesize response
    response = stream_and_synthesize_response(user_input)
    print(f"Full response: {response}")

    # Use wrapper in context manager to lease control, turn on E-Stop, power on the robot and stand up at start
    # and to return lease + sit down at the end
    with SpotController(username=SPOT_USERNAME, password=SPOT_PASSWORD, robot_ip=ROBOT_IP) as spot:
        time.sleep(2)
        capture_image()
        # Move head to specified positions with intermediate time.sleep
        spot.move_head_in_points(yaws=[0.2, 0],
                                 pitches=[0.3, 0],
                                 rolls=[0.4, 0],
                                 sleep_after_point_reached=1)
        capture_image()
        time.sleep(3)

        # Make Spot to move by goal_x meters forward and goal_y meters left
        spot.move_to_goal(goal_x=0.5, goal_y=0)
        time.sleep(3)
        capture_image()

        # Control Spot by velocity in m/s (or in rad/s for rotation)
        spot.move_by_velocity_control(v_x=-0.3, v_y=0, v_rot=0, cmd_duration=2)
        capture_image()
        time.sleep(3)

if __name__ == '__main__':
    main()
