import time
import azure.cognitiveservices.speech as speechsdk
import os
import numpy as np

class SpeechToTextManager:
    azure_speechconfig = None
    azure_audioconfig = None
    azure_speechrecognizer = None

    def __init__(self):
        # Creates an instance of a speech config with specified subscription key and service region.
        # Replace with your own subscription key and service region (e.g., "westus").
        try:
            self.azure_speechconfig = speechsdk.SpeechConfig(subscription=os.getenv('AZURE_TTS_KEY'), region=os.getenv('AZURE_TTS_REGION'))
        except TypeError:
            exit("Ooops! You forgot to set AZURE_TTS_KEY or AZURE_TTS_REGION in your environment!")
        self.stop_listening_flag = False
        self.accuracy_scores = []
        self.pronunciation_scores = []
        self.completeness_scores = []
        self.fluency_scores = []
    
    def stop_listening(self):
        self.stop_listening_flag = True
        
    def send_message(self,message,speaker=None):
        pass
        
    def speechtotext_from_mic(self,lang_code):
        self.azure_speechconfig.speech_recognition_language=lang_code
        self.azure_audioconfig = speechsdk.audio.AudioConfig(use_default_microphone=True)
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig)

        print("Speak into your microphone.")
        speech_recognition_result = self.azure_speechrecognizer.recognize_once_async().get()
        text_result = speech_recognition_result.text

        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("Recognized: {}".format(speech_recognition_result.text))
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")

        print(f"We got the following text: {text_result}")
        return text_result
        
        
    def pronunciation_check(self, filename, reference_text,lang_code):
        """performs one-shot speech recognition with input from an audio file, showing detailed recognition results
        including word-level timing and pronunciation assessment """

        # Ask for detailed recognition result
        # speech_config.output_format = speechsdk.OutputFormat.Detailed

        # If you also want word-level timing in the detailed recognition results, set the following.
        # Note that if you set the following, you can omit the previous line
        #   "speech_config.output_format = speechsdk.OutputFormat.Detailed",
        # since word-level timing implies detailed recognition results.
        self.azure_speechconfig.speech_recognition_language=lang_code
        self.azure_audioconfig = speechsdk.AudioConfig(filename=filename)
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig)
        
        try:
            self.azure_speechconfig.request_word_level_timestamps()
        except:
            print("Error in requesting word_level_timestamps ")
        
        print("Listening to the file \n")
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.FivePoint,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True)
        pronunciation_config.apply_to(self.azure_speechrecognizer)

        result = self.azure_speechrecognizer.recognize_once_async().get()

        # Check the result
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            pronunciation_result = speechsdk.PronunciationAssessmentResult(result)
            print('Pronunciation assessment completed for: {}'.format(result.text))
            
            # Store scores in arrays
            self.accuracy_scores.append(pronunciation_result.accuracy_score)
            self.pronunciation_scores.append(pronunciation_result.pronunciation_score)
            self.completeness_scores.append(pronunciation_result.completeness_score)
            self.fluency_scores.append(pronunciation_result.fluency_score)
            
            # print('  Word-level details:')
            # for idx, word in enumerate(pronunciation_result.words):
            #     print('    {}: word: {}\taccuracy score: {}\terror type: {};'.format(
            #         idx + 1, word.word, word.accuracy_score, word.error_type
            #     ))

        elif result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(result.no_match_details))
        elif result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                    
    def speechtotext_from_file(self, filename,lang_code):

        self.azure_speechconfig.speech_recognition_language= lang_code
        self.azure_audioconfig = speechsdk.AudioConfig(filename=filename)
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig)

        print("Listening to the file \n")
        speech_recognition_result = self.azure_speechrecognizer.recognize_once_async().get()

        if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
            print("Recognized: \n {}".format(speech_recognition_result.text))
        elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
            print("No speech could be recognized: {}".format(speech_recognition_result.no_match_details))
        elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
            cancellation_details = speech_recognition_result.cancellation_details
            print("Speech Recognition canceled: {}".format(cancellation_details.reason))
            if cancellation_details.reason == speechsdk.CancellationReason.Error:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")

        return speech_recognition_result.text
    
    def display_average_scores(self):
        if not self.accuracy_scores:
            print("No pronunciation assessments were performed.")
            return "No pronunciation assessments were performed."

        avg_accuracy = np.mean(self.accuracy_scores)
        avg_pronunciation = np.mean(self.pronunciation_scores)
        avg_completeness = np.mean(self.completeness_scores)
        avg_fluency = np.mean(self.fluency_scores)

        scores_message = ('Average pronunciation assessment scores:\n'
                          f'    Accuracy score: {avg_accuracy:.2f}, '
                          f'pronunciation score: {avg_pronunciation:.2f}, '
                          f'completeness score: {avg_completeness:.2f}, '
                          f'fluency score: {avg_fluency:.2f}')
        return scores_message

    def speechtotext_from_file_continuous(self, filename,lang_code):
        self.azure_speechconfig.speech_recognition_language= lang_code
        self.azure_audioconfig = speechsdk.audio.AudioConfig(filename=filename)
        self.azure_speechrecognizer = speechsdk.SpeechRecognizer(speech_config=self.azure_speechconfig, audio_config=self.azure_audioconfig)

        done = False
        def stop_cb(evt):
            print('CLOSING on {}'.format(evt))
            nonlocal done
            done = True

        # These are optional event callbacks that just print out when an event happens.
        # Recognized is useful as an update when a full chunk of speech has finished processing
        #self.azure_speechrecognizer.recognizing.connect(lambda evt: print('RECOGNIZING: {}'.format(evt)))
        self.azure_speechrecognizer.recognized.connect(lambda evt: print('RECOGNIZED: {}'.format(evt)))
        self.azure_speechrecognizer.session_started.connect(lambda evt: print('SESSION STARTED: {}'.format(evt)))
        self.azure_speechrecognizer.session_stopped.connect(lambda evt: print('SESSION STOPPED {}'.format(evt)))
        self.azure_speechrecognizer.canceled.connect(lambda evt: print('CANCELED {}'.format(evt)))

        # These functions will stop the program by flipping the "done" boolean when the session is either stopped or canceled
        self.azure_speechrecognizer.session_stopped.connect(stop_cb)
        self.azure_speechrecognizer.canceled.connect(stop_cb)

        # This is where we compile the results we receive from the ongoing "Recognized" events
        all_results = []
        def handle_final_result(evt):
            all_results.append(evt.result.text)
        self.azure_speechrecognizer.recognized.connect(handle_final_result)

        # Start processing the file
        print("Now processing the audio file...")
        self.azure_speechrecognizer.start_continuous_recognition()
        
        # We wait until stop_cb() has been called above, because session either stopped or canceled
        while not done:
            time.sleep(.5)

        # Now that we're done, tell the recognizer to end session
        # NOTE: THIS NEEDS TO BE OUTSIDE OF THE stop_cb FUNCTION. If it's inside that function the program just freezes. Not sure why.
        self.azure_speechrecognizer.stop_continuous_recognition()

        final_result = " ".join(all_results).strip()
        print(f"\n\nHeres the result we got from contiuous file read!\n\n{final_result}\n\n")
        return final_result
    
