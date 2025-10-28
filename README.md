# AI_Tabular_Submit-Retrieve
Application for prompt engineering and automated submission of tabular data to OpenAI Azure endpoint with retrieval and parsing of returning data.

1. Use the query_formatter to prepare a query based on your tabular text dataset.
2. Add your own Azure OPENAI endpoint URL and key to the submit-retrieve script.
3. Load your data and prompt into the submit-retrieve application to submit one row at a time to the LLM. Reponses are parsed and added to your table. Upon completion, you can export as excel or text.
4. A test prompt and synthetic text data file are provide as examples. These will load on click if the two files are in same directory as the *.py files.
