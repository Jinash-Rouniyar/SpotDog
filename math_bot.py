from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import (
     PromptTemplate,
     SystemMessagePromptTemplate,
     HumanMessagePromptTemplate,
     ChatPromptTemplate,
 )

output_parser = StrOutputParser()
chat_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.2) #experiment with temp values 0.2 - 0.4

#Math Bot
math_system_template_str = """
You are an experienced SAT Math tutor. Guide students through problems step-by-step, helping them reach the correct answer without providing it directly. Your responses should be concise, typically 1-3 sentences. Follow these guidelines:

1. Analyze the provided question, answer explanation, and options (if available).
2. If graphical or tabular data is included, incorporate it into your explanations.
3. Based on the answer explanation, break down the problem into small, manageable steps.
4. For each step:
   a. Provide a hint or ask a leading question to guide the student's thinking.
   b. Wait for the student's response before moving to the next step.
   c. If the student struggles, offer more detailed guidance without revealing the answer.
5. Encourage the student to perform calculations or apply concepts independently.
6. Validate correct steps with brief positive reinforcement.
7. Gently redirect incorrect steps by asking the student to reconsider or by providing a small hint.
8. If needed, explain relevant mathematical concepts concisely.
9. Guide the student towards the final answer, ensuring they understand each step.
10. Congratulate the student when they successfully solve the problem.

Maintain a supportive and patient tone throughout. Adapt your guidance based on the student's responses and the chat history. Focus on developing the student's problem-solving skills rather than simply providing answers.

Remember to keep the conversation natural and flowing, similar to a one-on-one tutoring session. Ask questions frequently to keep the student engaged and to check their understanding.

You will be provided with:
Question: {question}
Answer Explanation: {answer_exp}
Chat History: {chat_history}
"""

math_system_prompt = SystemMessagePromptTemplate(
    prompt=PromptTemplate(
        input_variables=["question","answer_exp", "chat_history"],
        template=math_system_template_str 

    )
)

math_human_prompt = HumanMessagePromptTemplate(
    prompt=PromptTemplate(
        input_variables=["student_input"],
        template="{student_input}"
    )
)

math_messages = [math_system_prompt, math_human_prompt]

math_prompt_template = ChatPromptTemplate(
    input_variables=["question","answer_exp", "chat_history","student_input"],
    messages=math_messages,
)


math_chain = (
    {
        "question": RunnablePassthrough(),
        "answer_exp": RunnablePassthrough(),
        "chat_history": RunnablePassthrough(),
        "student_input": RunnablePassthrough()
    }
    | math_prompt_template
    | chat_model
    | StrOutputParser()
)
# question = "Vivian bought party hats and cupcakes for $71. Each package of party hats cost $3, and each cupcake cost $1 . If Vivian bought 10 packages of party hats, how many cupcakes did she buy?"
# answer_exp = "The correct answer is 41. The number of cupcakes Vivian bought can be found by first finding the amount Vivian spent on cupcakes. The amount Vivian spent on cupcakes can be found by subtracting the amount Vivian spent on party hats from the total amount Vivian spent. The amount Vivian spent on party hats can be found by multiplying the cost per package of party hats by the number of packages of party hats, which yields $3 . 10 or $30. Subtracting the amount Vivian spent on party hats, $30, from the total amount Vivian spent, $71, yields $71 - $30, or $41. Since the amount Vivian spent on cupcakes was $41 and each cupcake cost $1, it follows that Vivian bought 41 cupcakes."
question = "x^2+7x+10=0"
answer_exp = "The correct answer is -2 and -5. To solve the quadratic equation x^2 + 7x + 10 = 0, we can use the quadratic formula, which is given by x = [-b ± sqrt(b^2 - 4ac)] / 2a. Here, a = 1, b = 7, and c = 10. First, we calculate the discriminant, which is b^2 - 4ac. Substituting the values of a, b, and c, we get 7^2 - 4(1)(10) = 49 - 40 = 9. The square root of 9 is 3, so we have x = [-7 ± sqrt(9)] / 2(1). This simplifies to x = [-7 ± 3] / 2. Therefore, the solutions are x = [-7 + 3] / 2 = -2 and x = [-7 - 3] / 2 = -5. So, the roots of the quadratic equation x^2 + 7x + 10 = 0 are x = -2 and x = -5."
