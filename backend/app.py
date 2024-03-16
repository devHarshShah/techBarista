import base64
import logging
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)
import os
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Import the CORS middleware
from pydantic import BaseModel
import requests
import asyncio
import sys
from main import main, summarize_repo, get_structure_comb_dict
from fastapi.responses import RedirectResponse
from fastapi.responses import RedirectResponse

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

app = FastAPI()

# Add the CORS middleware to your FastAPI application
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],
)

token = os.getenv('GITHUB_TOKEN')

def get_repo_structure_comb(repo_url, path=''):
    # Extract the owner and repo name from the URL
    owner, repo = repo_url.split('github.com/')[-1].split('/')
    
    # GitHub API URL for the repo contents
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    
    # Send a GET request to GitHub API
    headers = {'Authorization': f'token {token}'}
    response = requests.get(api_url, headers=headers)
    # If the request was successful, process the JSON response
    if response.status_code == 200:
        contents = response.json()
        structure = {'name': path.split('/')[-1] if path else repo, 'type': 'dir', 'content': [], 'url': api_url, 'api_url': api_url}
        for item in contents:
            if item['type'] == 'dir':
                # If the item is a directory, fetch its contents recursively
                item_structure = get_repo_structure_comb(repo_url, item['path'])
                structure['content'].append(item_structure)
            else:
                # If the item is a file, add it to the structure
                if str(api_url)[-1]=="/":
                    structure['content'].append({
                    'name': item['name'],
                    'type': 'file',
                    'path': item['path'],
                    'url': item['html_url'],
                    'api_url': api_url+item['name'],
                    'content': base64.b64decode(item['content']).decode('utf-8') if 'content' in item else "None"
                })
                else:
                    
                    structure['content'].append({
                        'name': item['name'],
                        'type': 'file',
                        'path': item['path'],
                        'url': item['html_url'],
                        'api_url': api_url+"/"+item['name'],
                        'content': base64.b64decode(item['content']).decode('utf-8') if 'content' in item else "None"
                    })
        return structure
    else:
        return None
# Get the personal access token from the user


def get_repo_structure_clean(repo_url, path=''):
    # Extract the owner and repo name from the URL
    owner, repo = repo_url.split('github.com/')[-1].split('/')
    
    # GitHub API URL for the repo contents
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    
    # Send a GET request to the GitHub API
    headers = {'Authorization': f'token {token}'}
    response = requests.get(api_url, headers=headers)
    
    
    # If the request was successful, process the JSON response
    if response.status_code == 200:
        contents = response.json()
        structure = []
        for item in contents:
            if item['type'] == 'dir':
                # If the item is a directory, fetch its contents recursively
                item_structure = get_repo_structure_clean(repo_url, item['path'])
                
                structure.append({
                    'name': item['name'],
                    'type': 'dir',
                    'contents': item_structure
                })
            else:
                # If the item is a file, add it to the structure
                structure.append({
                    'name': item['name'],
                    'type': 'file'
                })
        return structure
    else:
        return None
    
def get_repo_structure_blob(repo_url, path=''):
    # Extract the owner and repo name from the URL
    owner, repo = repo_url.split('github.com/')[-1].split('/')
    # GitHub API URL for the repo contents
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    # Send a GET request to the GitHub API
    headers = {'Authorization': f'token {token}'}
    response = requests.get(api_url, headers=headers)
    contents = response.json()
    if response.status_code == 200:
        return contents
    else:
        return None


# Define request models
class RepoUrl(BaseModel):
    key: str

class QueryCodeUrl(BaseModel):
    codeurl: str = 'None'
    query: str = ''
    url: str = ''

class RepoUrlFilePath(BaseModel):
    repo_url: str
    file_path: str

# Define your routes
@app.post('/get_structure_clean')
async def get_structure_clean(data: RepoUrl):
    repo_url = data.key
    structure = get_repo_structure_clean(repo_url)
    return {'clean': structure}

@app.post('/get_structure_blob')
async def get_structure_blob(data: RepoUrl):
    repo_url = data.key
    blob = get_repo_structure_blob(repo_url)
    return {'blob': blob}

@app.post('/get_structure_comb')
async def get_structure_combine(data: RepoUrl):
    repo_url = data.key
    blob =  get_repo_structure_comb(repo_url)
    return {'blob': blob}

@app.post('/ask_code_llm')
async def askCode(data: QueryCodeUrl):
    question = data.query
    codeurl = data.codeurl
    if codeurl == 'None' and question.strip() == '':
        return RedirectResponse(url='/summarize_using_llm')
    response = await main(question, codeurl)
    return {'response': response, 'question': question, 'codeurl': codeurl}



@app.post('/summarize_using_llm')
async def sumCode(data: QueryCodeUrl):
    try:
        codeurl = data.url
        logging.info("Received codeurl: %s", codeurl)
        stru = await get_structure_comb_dict(codeurl)
        logging.info("Got structure: %s", stru)
        response = await summarize_repo(stru,token)
        logging.info("Got response: %s", response)
        return {'response': response}, 200
    except Exception as e:
        logging.exception("An error occurred: %s", e)
        return {'error': str(e)}, 500
    
    
@app.post('/get_file_url')
async def get_file_url(data: RepoUrlFilePath):
    repo_url = data.repo_url
    file_path = data.file_path
    owner, repo = repo_url.split('github.com/')[-1].split('/')
    file_url = f'https://api.github.com/repos/{owner}/{repo}/contents{file_path}'
    return {'file_url': file_url}