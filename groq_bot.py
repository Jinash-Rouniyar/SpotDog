import dotenv
import os
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_community.vectorstores import Chroma
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import (
     PromptTemplate,
     SystemMessagePromptTemplate,
     HumanMessagePromptTemplate,
     ChatPromptTemplate,
 )
from langchain_groq import ChatGroq

dotenv.load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")

review_system_template_str = """
You are controlling a Spot robot equipped with a vision camera. Based on the surroundings that you see, provide one of the following instructions for the robot's movement:

- "quit" if no action is required or if the session should stop
- "up" if the path ahead is clear and the robot should move forward
- "down" if the robot should reverse
- "left" if the robot needs to turn left and move forward
- "right" if the robot needs to turn right and move forward
- "turn" if the robot should perform a smooth 360-degree turn
- "scan" if the robot should move its head down and capture frames

Please base your decision on the camera input.

Provide only the instruction in your response.
"""

review_system_prompt = SystemMessagePromptTemplate(
     prompt=PromptTemplate(
         input_variables=[], template=review_system_template_str
     )
 )
review_human_prompt = HumanMessagePromptTemplate(
     prompt=PromptTemplate(
         input_variables=["question"], template="{question}"
     )
 )

messages = [review_system_prompt, review_human_prompt]

review_prompt_template = ChatPromptTemplate(
     input_variables=["question"],
     messages=messages,
 )
output_parser = StrOutputParser()
chat_model = ChatGroq(
            api_key=groq_api_key, 
            model_name='llama3-groq-8b-8192-tool-use-preview',
            temperature = 0
        )

groq_chain = (
    {"question": RunnablePassthrough()}
    | review_prompt_template
    | chat_model
    | StrOutputParser()
)

