import os
import time
import base64
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
import logging

# Initialize Azure Speech SDK
speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'), region=os.environ.get('SPEECH_REGION'))
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
subscription_key = os.environ.get('SPEECH_KEY')
region = os.environ.get('SPEECH_REGION')
# Initialize SpeechToTextManager
speech_to_text_manager = SpeechToTextManager()

def capture_image():
    camera_capture = cv2.VideoCapture(0)
    rv, image = camera_capture.read()
    print(f"Image Dimensions: {image.shape}")
    camera_capture.release()
def main():
    try:
        # Play default voice
        default_voice = os.path.join(os.getcwd(), "default.wav")
        logging.info(f"Playing default voice: {default_voice}")
        os.system(f"ffplay -nodisp -autoexit -loglevel quiet {default_voice}")

        # Record audio
        cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 {WAVE_OUTPUT_FILENAME}'
        logging.info(f"Recording audio with command: {cmd}")
        os.system(cmd)

        # Transcribe the recorded audio
        try:
            user_input = speech_to_text_manager.speechtotext_from_file(WAVE_OUTPUT_FILENAME, LANG_CODE)
            logging.info(f"Transcribed user input: {user_input}")
        except Exception as e:
            logging.error(f"Error in speech-to-text conversion: {str(e)}")
            raise

        # Process input (math chain)
        try:
            output_text = math_chain.invoke({
                "question": question,
                "answer_exp": answer_exp,
                "student_input": user_input
            })
        except Exception as e:
            logging.error(f"Error in math processing: {str(e)}")
            raise

        # Text-to-speech using Azure
        endpoint_url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-16khz-32kbitrate-mono-mp3'
        }

        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
            <voice name='en-US-AnaNeural'>
                {output_text}
            </voice>
        </speak>
        """

        try:
            response = requests.post(endpoint_url, headers=headers, data=ssml)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            
            tts_filename = "abcd.mp3"
            with open(tts_filename, 'wb') as f:
                f.write(response.content)
            logging.info(f"TTS audio saved to {tts_filename}")
            
            os.system(f"ffplay -nodisp -autoexit -loglevel quiet {tts_filename}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error in TTS API call: {str(e)}")
            raise

    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
    # response = stream_and_synthesize_response(user_input)

    # Use wrapper in context manager to lease control
    with SpotController(username=SPOT_USERNAME, password=SPOT_PASSWORD, robot_ip=ROBOT_IP) as spot:
        time.sleep(2)
        capture_image()
        
        # Move head to specified positions
        spot.move_head_in_points(yaws=[0.2, 0],
                               pitches=[0.3, 0],
                               rolls=[0.4, 0],
                               sleep_after_point_reached=1)
        capture_image()
        time.sleep(3)

        # Move Spot forward
        spot.move_to_goal(goal_x=0.5, goal_y=0)
        time.sleep(3)
        capture_image()

        # Control Spot by velocity
        spot.move_by_velocity_control(v_x=-0.3, v_y=0, v_rot=0, cmd_duration=2)
        capture_image()
        time.sleep(3)

if __name__ == '__main__':
    main()
    
'''
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

    # Create a temporary file for the audio stream
    with tempfile.NamedTemporaryFile(suffix='.raw', delete=False) as temp_audio_file:
        temp_filename = temp_audio_file.name
        
        # Start ffplay process for streaming
        ffplay_process = subprocess.Popen(
            ['ffplay', 
             '-f', 's16le',  # Format: 16-bit little-endian
             '-ar', '16000',  # Sample rate: 16kHz
             '-ac', '1',      # Mono audio
             '-i', 'pipe:0',  # Read from stdin
             '-nodisp',       # No video display
             '-autoexit'      # Exit when done
            ],
            stdin=subprocess.PIPE,
            bufsize=0  # Unbuffered
        )

        full_response = ""
        for text_chunk in stream_output():
            full_response += text_chunk
            
            # Generate speech from the text chunk
            result = speech_synthesizer.speak_text_async(text_chunk).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Write audio data directly to ffplay's stdin
                try:
                    ffplay_process.stdin.write(result.audio_data)
                    ffplay_process.stdin.flush()
                except BrokenPipeError:
                    print("Audio stream was closed")
                    break
            else:
                print(f"Speech synthesis failed: {result.reason}")

        # Close the stdin pipe and wait for ffplay to finish
        try:
            ffplay_process.stdin.close()
        except:
            pass
        ffplay_process.wait()

    return full_response


import os
import time
from spot_controller import SpotController
import cv2

ROBOT_IP = "192.168.80.3"#os.environ['ROBOT_IP']
SPOT_USERNAME = "admin"#os.environ['SPOT_USERNAME']
SPOT_PASSWORD = "2zqa8dgw7lor"#os.environ['SPOT_PASSWORD']


def capture_image():
    camera_capture = cv2.VideoCapture(0)
    rv, image = camera_capture.read()
    print(f"Image Dimensions: {image.shape}")
    camera_capture.release()


def main():
    #endpoint_url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1' # Headers for the request headers = { 'Ocp-Apim-Subscription-Key': subscription_key, 'Content-Type': 'application/ssml+xml', 'X-Microsoft-OutputFormat': 'audio-16khz-32kbitrate-mono-mp3' # Output audio format } 

    #example of using micro and speakers
    print("Start recording audio")
    sample_name = "aaaa.wav"
    cmd = f'arecord -vv --format=cd --device={os.environ["AUDIO_INPUT_DEVICE"]} -r 48000 --duration=10 -c 1 {sample_name}'
    print(cmd)
    os.system(cmd)
    print("Audio Captured")
	user_input = speech_to_text_manager.speechtotext_from_file(WAVE_OUTPUT_FILENAME, LANG_CODE)
    
   endpoint_url = f'https://{region}.tts.speech.microsoft.com/cognitiveservices/v1'
        headers = {
            'Ocp-Apim-Subscription-Key': subscription_key,
            'Content-Type': 'application/ssml+xml',
            'X-Microsoft-OutputFormat': 'audio-16khz-32kbitrate-mono-mp3'
        }

        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
            <voice name='en-US-AnaNeural'>
                {user_input}
            </voice>
        </speak>
        """
        response = requests.post(endpoint_url, headers=headers, data=ssml)

        if response.status_code == 200:
            # Generate a unique filename for the Azure TTS output
            tts_filename = f"abcd.mp3"
            
            # Save the audio file
            with open(tts_filename, 'wb') as f:
                f.write(response.content)
                
    os.system(f"ffplay -nodisp -autoexit -loglevel quiet {“abcd.mp3}")
        # # Capture image

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



'''