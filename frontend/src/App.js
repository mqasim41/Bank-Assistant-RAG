import React, { useState } from 'react';
import { PaperAirplaneIcon, DocumentIcon } from '@heroicons/react/24/outline';

function App() {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState('');
  const [loading, setLoading] = useState(false);
  const [file, setFile] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
      // First upload the file if one is selected
      if (file) {
        const fileFormData = new FormData();
        fileFormData.append('doc', file);
        await fetch('http://localhost:8000/add-document', {
          method: 'POST',
          body: fileFormData,
        });
      }

      // Then send the question
      const response = await fetch('http://localhost:8000/query', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question }),
      });
      const data = await response.json();
      setResponse(data.answer);
    } catch (error) {
      console.error('Error:', error);
      setResponse('Sorry, there was an error processing your request.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-bold text-gray-900 font-serif">Bank Support Assistant</h1>
          <p className="mt-3 text-lg text-gray-600">Ask any questions about our banking services</p>
        </div>

        <div className="bg-white rounded-lg shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label htmlFor="question" className="block text-sm font-medium text-gray-700 mb-2">
                Your Question
              </label>
              <div className="mt-1">
                <textarea
                  id="question"
                  name="question"
                  rows={4}
                  className="shadow-sm focus:ring-blue-500 focus:border-blue-500 block w-full sm:text-sm border-gray-300 rounded-md p-4 font-sans text-base"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="Type your question here..."
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Upload Document (Optional)
              </label>
              <div className="mt-1 flex items-center">
                <input
                  type="file"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-gray-500
                    file:mr-4 file:py-2 file:px-4
                    file:rounded-md file:border-0
                    file:text-sm file:font-semibold
                    file:bg-blue-50 file:text-blue-700
                    hover:file:bg-blue-100"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || !question.trim()}
                className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors duration-200"
              >
                {loading ? (
                  'Processing...'
                ) : (
                  <>
                    <PaperAirplaneIcon className="h-5 w-5 mr-2" />
                    Submit Question
                  </>
                )}
              </button>
            </div>
          </form>

          {response && (
            <div className="mt-8">
              <h2 className="text-xl font-medium text-gray-900 mb-3">Response</h2>
              <div className="bg-gray-50 rounded-lg p-6">
                <p className="text-gray-700 whitespace-pre-wrap text-base leading-relaxed">{response}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App; 