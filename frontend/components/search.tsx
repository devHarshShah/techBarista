import React, { useState, useEffect, useRef } from 'react';
import FolderStructure from './folderstructure';
import { Input, Button } from '@nextui-org/react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';

interface Item {
  name: string;
  type: string;
  contents?: Item[];
}

interface ChatItem {
  type: 'question' | 'response';
  content: string;
}

const Search = ({ data }: { data: Item[] }) => {
  const [inputValue, setInputValue] = useState(''); // add state for the input value
  const [selectedFile, setSelectedFile] = useState('None'); // add state for the selected file
  const [path, setPath] = useState('');
  const [chatHistory, setChatHistory] = useState<ChatItem[]>([]); // add state for the chat history
  const [loading, setLoading] = useState(true); // add state for loading
  const [summary, setSummary] = useState('Loading summary of repo...'); // add state for the summary

  const hasFetchedSummary = useRef(false);

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(event.target.value); // update the input value when the input changes
  };

  const handleButtonClick = async () => {
    setInputValue('');
    // Check if a file has been selected and an input value has been entered
    if (!inputValue) {
      console.error('A file must be selected and a query must be entered before sending a request');
      return;
    }

    // Add the question to the chat history
    setChatHistory((prevChatHistory) => [...prevChatHistory, { type: 'question', content: inputValue }]);

    // Get the URL of the selected file
    let repo = localStorage.getItem('repo-link');
    const response = await fetch('http://127.0.0.1:8000/get_file_url', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        repo_url: repo,
        file_path: selectedFile === 'None' ? 'None' : path,
      }),
    });

    if (!response.ok) {
      console.error('Failed to get the file URL');
      return;
    }

    const data = await response.json();
    const fileUrl = data.file_url;
    const searchResponse = await fetch('http://127.0.0.1:8000/ask_code_llm', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        codeurl: fileUrl,
        query: inputValue,
      }),
    });

    if (!searchResponse.ok) {
      console.error('Search request failed');
      return;
    }

    const searchData = await searchResponse.json();

    console.log(searchData);

    // Add the response to the chat history
    setChatHistory((prevChatHistory) => [...prevChatHistory, { type: 'response', content: searchData.response }]);
  };

  const handleFileSelect = async (filePath: string, fileName: string) => {
    // update the selected file when a file is clicked
    setSelectedFile(fileName === '' ? 'None' : fileName);
    let fullpath = filePath + '/' + fileName;
    setPath(fullpath);
  };

  const fetchSummaryAndUpdateChat = async () => {
    let repo = localStorage.getItem('repo-link');
    try {
      const response = await axios.post('http://127.0.0.1:8000/ask_code_llm', {
        url: repo,
        codeurl: "None",
        query:""
      });

      setSummary(response.data[0].response);
      setLoading(false);

      // Add the summary as the first response in the chat history
      setChatHistory((prevChatHistory) => [...prevChatHistory, { type: 'response', content: response.data[0].response }]);
    } catch (error) {
      console.error('Failed to get the summary');
      setSummary('Failed to load summary');
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!hasFetchedSummary.current) {
      fetchSummaryAndUpdateChat();
      hasFetchedSummary.current = true;
    }
  }, []);

  return (
    <div className="flex flex-row h-[82vh]">
      <div className="custom-scrollbar w-[20%] p-5 overflow-y-auto">
        <FolderStructure data={data} onFileSelect={handleFileSelect} />
      </div>
      <div className="flex flex-col w-[80%] justify-end ml-4">
        <div className="flex flex-col custom-scrollbar w-full p-5 overflow-y-auto">
          {chatHistory.map((item, index) => {
            if (item.type === 'question') {
              return (
                <div key={index} className="p-2 rounded-lg my-1 border-2 border-blue-700 bg-blue-200 bg-opacity-25 text-blue-200 inline-block mr-auto" style={{ overflowWrap: 'break-word', wordBreak: 'break-word' }}>
                  <ReactMarkdown>{item.content}</ReactMarkdown>
                </div>
              );
            } else {
              return (
                <div key={index} className="p-2 rounded-lg my-1 border-2 border-green-700 bg-opacity-25 bg-green-200 text-green-200 inline-block ml-auto w-[95%]" style={{ overflowWrap: 'break-word', wordBreak: 'break-word' }}>
                  <ReactMarkdown>{item.content}</ReactMarkdown>
                </div>
              );
            }
          })}
        </div>
        <div className="w-full p-10 flex items-center">
          <div className="w-[30%] border-2 border-purple-500 rounded-l-xl p-[0.36rem] flex items-center justify-center bg-purple-200 bg-opacity-[20%] text-purple-500">{selectedFile === 'None' ? 'None' : selectedFile}</div>
          <Input type="email" variant="bordered" radius="none" value={inputValue} onChange={handleInputChange} />
          <Button color="primary" radius="none" style={{ backgroundColor: 'rgba(59, 130, 246, 0.3)', border: '2px solid rgb(59,130,246)', color: 'rgb(59,130,246)', fontWeight: 'bold' }} className="rounded-r-xl" onClick={handleButtonClick}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
};

export default Search;