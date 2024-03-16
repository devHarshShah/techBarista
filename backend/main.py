import json
from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from Searcher import Searcher
import requests
import base64

from chat_hist import chathistory

global repo_summary

load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ghtoken = "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"

llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=GOOGLE_API_KEY)

def get_github_file_content(url:str, token:str):
    headers = {'Authorization': f'token {token}'}
    response = requests.get(url, headers=headers)
    response_json = response.json()

    if 'content' in response_json:
        content_base64 = response_json['content']
        try:
            content = base64.b64decode(content_base64).decode('utf-8')
        except UnicodeDecodeError:
            print(f"Cannot decode file as text.")
            content = None
        return content
    elif 'message' in response_json:
        return response_json['message']
    else:
        return "Error: Unexpected response"

def create_search_qns(question, context):

    SQprompt = PromptTemplate.from_template("""As an AI trained to generate questions, your task is to create a set of questions that delve deeper into a given topic, using a provided context (typically a code file) as a reference. Your questions should guide the user towards the answers they seek.

Please adhere to the following guidelines:
1) Do not repeat questions.
2) Ensure your questions are relevant to both the given question and context.
3) Generate a minimum of 1 and a maximum of 4 questions.
4) Your questions should explore the topic in depth, based on the given question.
5) The output should be a list of questions.
6) The questions should be likely to be asked by a human, given the context and question.
7) The questions MUST be relevant to the CONTEXT.
8) Be specific to the given context in your questions.
9) Avoid vague language in your questions. Be specific and direct.

For example:
Given question: "What is the purpose of this code?"
Given context: "Assume, This is a code file that contains a class that is used to create a new user.(In reality it will be code)"
Output: ["What is a class?", "How does one create a new class?", "What is the purpose of a class?", "How does this code manage users?"]

Now, let's generate questions for the given question: {question} and the given context: {context}.""")

    chain = SQprompt | llm | StrOutputParser()
    search_qns = chain.invoke({"question": question, "context": context})
    search_qns = search_qns.split("\n")
    search_qns = [qn for qn in search_qns if qn]
    return search_qns


prompt = PromptTemplate.from_template("""As an AI chatbot, your role is to assist users in understanding code files. You will receive four inputs:
1) 'context': a code file
2) 'question': a user's query about the code
3) 'conversation history': the ongoing dialogue
4) 'search results': the results from a web search of the 'question' related to 'context'.

Your responses should be factual, professional, and friendly, strictly based on the provided code file. Your goal is to help users effectively understand and utilize the code.

Ensure your guidance covers various aspects of code comprehension, including structure, syntax, functionality, and best practices. Prioritize clarity, accuracy, and user-friendly interactions to deliver a positive user experience.

Please note:
- The output should be a string.
- Use the conversation history to provide contextually relevant responses.
- Aim for an output length of around 400 words, although this is not a strict limit.
- You may use the provided references in your final output if necessary.
- If asked to explain the code, use the actual code to clarify its functionality.

Now, let's generate a response for the given question: {question}, context: {context}, conversation history: {chathistory}, and search results: {searchresults}.""")


async def summarize_repo(api_response:dict, token):
    global repo_summary
    file_info = {}
    def process_items(items, file_info):
        for item in items:
            if item['type'] == 'file':
                file_info[item['api_url']] = item['path']
            elif item['type'] == 'dir':
                process_items(item['content'], file_info)

    file_info = {}
    process_items(api_response['blob']['content'], file_info)

    summarize_file_prompt = PromptTemplate.from_template("""As an AI chatbot, your role is to assist users in understanding code files. You will receive one input, 'context', which represents a code file in a Git repository.

Your task is to summarize the code file. You are expected to provide a concise summary, ideally under 50 words. However, if the file is extensive, the summary can extend up to 250 words.

Your summary should include the file's purpose, functionality, and any other pertinent details.

Please note:
- The output should be a string.
- The summary should be presented in a point-wise format for clarity.

Now, let's generate a summary for the given context: {context}.""")
    sum_file_chain = summarize_file_prompt | llm | StrOutputParser()
    file_summaries = []
    for fileurl, filepath in file_info.items():
        file = get_github_file_content(fileurl, token)
        summary = sum_file_chain.invoke({"context": file})
        file_summaries.append((filepath, summary))

    summarizer_prompt = PromptTemplate.from_template("""As an AI chatbot, your role is to assist users in understanding code files. You will receive one input, 'abt_files', which represents the file structure of an entire Git repository, along with summaries of each file.

Your task is to provide an overview of the code file's summary, summarizing their purpose, functionality, and their relationship with other files, based on the provided summaries.

Please adhere to the following guidelines:
- Maintain a friendly and professional demeanor.
- Provide factual assistance based on the contents of the provided code files.
- Prioritize clarity, accuracy, and user-friendly interactions.
- The output should be a string, presented in a point-wise format.
- The input will be a list of tuples, each containing a file path and a summary.
- Using the file path as identifier, figure out the relationship between the files and summarize them.
- Keep the output length between 400 and 1000 words, ideally around 600 words.
- Reflect the relationship between the files in your summary.

For example, if the path is '/src/app/index.js', the summary should reflect the relationship between the 'index.js' file, the 'app' folder, and the rest of the structure.

Now, let's generate an overview for the given repository information: {abt_files}.""")
    repo_sum_chain = summarizer_prompt | llm | StrOutputParser()
    repo_sum = repo_sum_chain.invoke({"abt_files": file_summaries})
    repo_summary = summarize_repo(api_response, ghtoken)
    return repo_sum

def summarize_dir(api_response_dir:dict, token):
    file_info = {}
    def process_items(items, file_info):
        for item in items:
            if item['type'] == 'file':
                file_info[item['url']] = item['path']
            elif item['type'] == 'dir':
                process_items(item['content'], file_info)

    file_info = {}
    process_items(api_response_dir['blob']['content'], file_info)

    summarize_file_prompt = PromptTemplate.from_template("""As an AI chatbot, your role is to assist users in understanding code files. You will receive one input, 'context', which represents a code file in a Git repository.

Your task is to summarize the code file. Aim to keep your summary under 150 words. Your summary should include the file's purpose, functionality, and any other pertinent details.

Please note:
- The output should be a string.
- The summary should be presented in a point-wise format for clarity.

Now, let's generate a summary for the given context: {context}.""")
    sum_file_chain = summarize_file_prompt | llm | StrOutputParser()
    file_summaries = []
    for fileurl, filepath in file_info.items():
        file = get_github_file_content(fileurl, token)
        summary = sum_file_chain.invoke({"context": file})
        file_summaries.append((filepath, summary))

    summarizer_dir_prompt = PromptTemplate.from_template("""As an AI chatbot, your role is to assist users in understanding code files. You will receive one input, 'abt_dir_files', which represents the file structure of a folder in a Git repository, along with summaries of each file.

Your task is to provide an overview of the code files, summarizing their purpose, functionality, and their relationship with other files, based on the provided summaries.

Please adhere to the following guidelines:
- Maintain a friendly and professional demeanor.
- Provide factual assistance based on the contents of the provided code files.
- Prioritize clarity, accuracy, and user-friendly interactions.
- The output should be a string, presented in a point-wise format.
- The input will be a list of tuples, each containing a file path and a summary.
- Keep the output length between 200 and 500 words, ideally around 300 words.
- Reflect the relationship between the files in your summary.

For example, if the path is '/src/app/index.js', the summary should reflect the relationship between the 'index.js' file, the 'app' folder, and the rest of the structure.

Now, let's generate an overview for the given repository information: {abt_dir_files}.""")
    dir_sum_chain = summarizer_dir_prompt | llm | StrOutputParser()
    dir_sum = dir_sum_chain.invoke({"abt_dir_files": file_summaries})
    return dir_sum


chain = prompt | llm | StrOutputParser()

searcher = Searcher()

async def main(question:str, codeurl="None") -> str:
    if question == "exit":
        return "Goodbye"

    gitfile = get_github_file_content(codeurl, ghtoken)
    searchquestions = create_search_qns(question, gitfile)
    searchresults = {}
    for qn in searchquestions:
        searchresults[qn] = await searcher.search_and_get_content(qn)

    if codeurl=="None":
        response = chain.invoke({"question": question, "context": "", "chathistory": chathistory[:10], "searchresults": searchresults, "repo_summary": repo_summary})
    else:
      response = chain.invoke({"question": question, "context":gitfile, "chathistory": chathistory[:10], "searchresults": searchresults, "repo_summary": repo_summary})

    chathistory.append((f"Human: {question}", f"AI: {response}", f"Search Results: {searchresults}"))
    return response


import httpx

async def get_structure_comb_dict(url):
    link = "http://127.0.0.1:8000/get_structure_comb"
    data = {
        "key": url
    }
    timeout = httpx.Timeout(10.0, connect=20.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(link, json=data)
    data = response.json()
    return data