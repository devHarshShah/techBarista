import base64
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware  # Import the CORS middleware
from pydantic import BaseModel
import requests
import asyncio
import sys
from main import main

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

token = ''

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
                structure['content'].append({
                    'name': item['name'],
                    'type': 'file',
                    'path': item['path'],
                    'url': item['html_url'],
                    'api_url': api_url,
                    'content': base64.b64decode(item['content']).decode('utf-8') if 'content' in item else None
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
    query: str
    codeurl: str

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
    response = await main(question, codeurl)
    return {'response': response}

@app.post('/summarize_using_llm')
async def sumCode(data: QueryCodeUrl):
    question = data.query
    codeurl = data.codeurl
    response = await main(question, codeurl)
    return {'response': response}

@app.post('/get_file_url')
async def get_file_url(data: RepoUrlFilePath):
    repo_url = data.repo_url
    file_path = data.file_path
    owner, repo = repo_url.split('github.com/')[-1].split('/')
    file_url = f'https://api.github.com/repos/{owner}/{repo}/contents{file_path}'
    return {'file_url': file_url}