# GUI to enable batch submission of tabular data one row at a time to AI LLM on Azure cloud
# For correct usage, load a text prompt generated with the partner application. The formatting
# of the prompt is key to signaling which data elements need to be captured from the AI responses
# You will need to specify your own URL for your AZURE_OPENAI_ENDPOINT and also your AZURE_OPENAI_KEY
# where indicated in the code.

import tkinter as tk
from tkinter import messagebox, ttk, filedialog, simpledialog
import pandas as pd
import re
import os
from openai import AzureOpenAI
import json
import requests
from openai import BadRequestError  # need to error catch if a prompt violates policy filters
import sys  # Import sys to exit the script
from datetime import datetime, timedelta



# URL and key for Azure OpenAI go here
client = AzureOpenAI(
    azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", "https://[copy URL for your AI endpoint here]/"),
    api_key=os.environ.get("AZURE_OPENAI_KEY", "[your open AI key goes here]"),
    api_version="2024-05-01-preview",
)

# Set the model type (eg. gpt 3.5, and specific name of the deployed model in our azure instance)
AZURE_OPENAI_MODEL = os.environ.get("AZURE_OPENAI_MODEL",
                                    "gpt-4o-mini")  # switch to 'gpt-4o' to use the gpt4o model (10x more expensive per token)
AZURE_OPENAI_MODEL_NAME = os.environ.get("AZURE_OPENAI_MODEL_NAME",
                                         "gpt-4o-mini")  # switch to 'gpt-4o' to use the gpt4o model

input_fields = []  # Initialize the input_fields list
df = pd.DataFrame()  # Initialize an empty DataFrame
assembled_prompt = ""  # Initialize assembled_prompt



def load_file():
    global inputfile
    global input_fields  # Declare input_fields as global
    inputfile = filedialog.askopenfilename(
        title="Select Tab-Delimited Text or Excel File",
        filetypes=[("All files", "*.*")]
    )
    if inputfile:
        ext = os.path.splitext(inputfile)[1].lower()
        global df  # Declare df as global
        try:
            if ext == '.txt':
                encodings = ['utf-8', 'Windows-1252']  # List of encodings to try
                for encoding in encodings:
                    try:
                        df = pd.read_csv(inputfile, sep='\t', encoding=encoding)
                        input_fields = df.columns.tolist()  # Create a list of headers
                        display_dataframe(df)
                        return  # Exit the function if successful
                    except Exception as e:
                        last_error = e  # Store the last error message
                messagebox.showerror("Error", f"Failed to load file: {last_error}")
            elif ext in ['.xls', '.xlsx']:
                df = pd.read_excel(inputfile)
                input_fields = df.columns.tolist()
                display_dataframe(df)
            else:
                messagebox.showerror("Error", "Unsupported file type selected.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")


def load_test_data():
    global inputfile
    global input_fields  # Declare input_fields as global
    inputfile = 'test_data.txt'
    try:
        global df  # Declare df as global
        df = pd.read_csv(inputfile, sep='\t')
        input_fields = df.columns.tolist()  # Create a list of headers
        display_dataframe(df)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load test data: {e}")


def display_dataframe(df):
    # Clear the Treeview
    for i in tree.get_children():
        tree.delete(i)

    # Insert new data into the Treeview
    for index, row in df.iterrows():
        tree.insert("", "end", values=list(row))

    # Update column headings
    tree["columns"] = list(df.columns)
    for col in df.columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center")


def load_prompt():
    global assembled_prompt  # Declare assembled_prompt as global
    filename = filedialog.askopenfilename(title="Select Prompt File", filetypes=[("Text files", "*.txt")])
    if filename:
        encodings = ['utf-8', 'Windows-1252']  # List of encodings to try
        for encoding in encodings:
            try:
                with open(filename, "r", encoding=encoding) as file:
                    assembled_prompt = file.read()
                text_prompt.delete(1.0, tk.END)  # Clear previous content
                text_prompt.insert(tk.END, assembled_prompt)  # Display loaded prompt

                # Parse for output fields
                parse_output_fields(assembled_prompt)
                return  # Exit the function if successful
            except Exception as e:
                last_error = e  # Store the last error message
        messagebox.showerror("Error", f"Failed to load prompt: {last_error}")
    else:
        messagebox.showwarning("Warning", "No file selected.")


def load_test_prompt():
    global assembled_prompt  # Declare assembled_prompt as global
    filename = 'test_promptv2.txt'
    try:
        with open(filename, "r") as file:
            assembled_prompt = file.read()
        text_prompt.delete(1.0, tk.END)  # Clear previous content
        text_prompt.insert(tk.END, assembled_prompt)  # Display loaded prompt

        # Parse for output fields
        parse_output_fields(assembled_prompt)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load test prompt: {e}")


def parse_output_fields(assembled_prompt):
    match = re.search(r"Output_Fields will be \[(.*?)\]", assembled_prompt)
    if match:
        output_headers = [header.strip() for header in match.group(1).split(',')]
        display_output_headers(output_headers)
        create_dataframe(output_headers)


def display_output_headers(output_headers):
    headers_str = ', '.join(output_headers)
    messagebox.showinfo("Output Items", f"The AI will attempt to output the following items:\n{headers_str}")


def create_dataframe(output_headers):
    # Load the original DataFrame
    original_df = pd.read_csv(inputfile, sep='\t')

    # Create a new DataFrame with the output headers as columns
    for header in output_headers:
        original_df[header] = ""  # Add new columns with empty values

    display_dataframe(original_df)  # Display the modified DataFrame in the original text area


def run_conversation_w_input0(input, assembled_prompt):
    messages = [{"role": "system", "content": f"""{assembled_prompt}
    """
                 },
                {"role": "user", "content": input}, ]

    # this is the actual chat completion API call
    print("evaluating", input)
    response = client.chat.completions.create(
        model=AZURE_OPENAI_MODEL,
        messages=messages,
    )
    print(response)
    return response


def send_query_to_ai(row_limit=None):
    global df  # Use the global DataFrame
    global assembled_prompt  # Use the global assembled_prompt
    processed_records = 0
    qc_record = ""  # capture the output of the LLM for any qc analysis needs
    cumulative_error_details = []  # capture prompts that triggered errors during processing for display at the end of execution
    stopping_number = row_limit if row_limit is not None else len(df)  # Limit to specified rows or all

    for index, row in df.iterrows():
        if processed_records >= stopping_number:
            break
        try:
            row_prep = '\t'.join(row[input_fields].astype(str))  # Generate the tab-delimited string
            processed_records += 1
            query = f""" {row_prep} ."""  # Keep triple quotes for this. Use f-string to insert the variables.
            results = run_conversation_w_input0(query, assembled_prompt)  # Ensure assembled_prompt is defined

            # Extract the content and remove the code block formatting
            json_content = results.choices[0].message.content.strip('```json\n').strip('```')

            # Now load the JSON data
            results_json = json.loads(json_content)  # converts the json to a dict!
            print("Results JSON:", results_json)  # check the data type of results_json

            if isinstance(results_json,
                          dict):  # Error Catching for occasional instances when chat completion comes back as a list
                for key, value in results_json.items():
                    df.at[index, key] = str(value)  # Convert value to string before updating dataframe
            elif isinstance(results_json, list):
                print("Received a list instead of a dictionary:", results_json)
                # Handle the list case as needed
            else:
                print("Unexpected response format:", results_json)

            # Update the displayed DataFrame and processed records counter
            display_dataframe(df)
            processed_label.config(text=f"Processed Records: {processed_records}")
            print(results_json)
            print("Processed records:", str(processed_records))
            qc_record += str(processed_records) + ": " + str(results_json) + "\n"
        except BadRequestError as e:  # catch errors due to inadvertent content policy violations in prompts
            print("Error occurred (bad request):", e)
            cumulative_error_details.append(e)
            cumulative_error_details.append(row_prep)
            continue
        except json.JSONDecodeError as er:  # catch errors due to LLM occasionally returning incorrect JSON format
            print("Error occurred (JSON decode):", er)
            cumulative_error_details.append(er)
            cumulative_error_details.append(row_prep)
            continue


def export_to_tsv():
    global df
    if df.empty:
        messagebox.showwarning("Warning", "No data to export.")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".txt",
                                             filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
    if file_path:
        df.to_csv(file_path, sep='\t', index=False)
        messagebox.showinfo("Success", "Data exported successfully as tab-delimited text.")


def export_to_xlsx():
    global df
    if df.empty:
        messagebox.showwarning("Warning", "No data to export.")
        return
    file_path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
    if file_path:
        df.to_excel(file_path, index=False)
        messagebox.showinfo("Success", "Data exported successfully as Excel file.")


def show_help():
    messagebox.showinfo("Help", "Contact Paraic Kenny: pakenny@gundersenhealth.org")


# Create main window
root = tk.Tk()
root.title("Emplify AI - Batch Query Submission")

# Input file section
frame_input = tk.Frame(root)
frame_input.pack(pady=10)

button_load = tk.Button(frame_input, text="Load Tab-Delimited Text or Excel data", command=load_file, bg='orange')
button_load.pack(side=tk.LEFT)

button_load_test_data = tk.Button(frame_input, text="Load Test Data", command=load_test_data, bg='orange')
button_load_test_data.pack(side=tk.LEFT)

# Create a Treeview for displaying DataFrame
tree = ttk.Treeview(root, show='headings')
tree.pack(pady=10, fill=tk.BOTH, expand=True)

# Create a scrollbar for the Treeview
scrollbar = ttk.Scrollbar(root, orient="vertical", command=tree.yview)
scrollbar.pack(side='right', fill='y')
tree.configure(yscroll=scrollbar.set)

# Load prompt section
label_load_prompt = tk.Label(root, text='Load Prompt File:')
label_load_prompt.pack(pady=10)

text_prompt = tk.Text(root, width=200, height=15, state='normal')  # Set height to 15 rows
text_prompt.pack(pady=5)

button_load_prompt = tk.Button(root, text="Load Prompt", command=load_prompt, bg='orange')
button_load_prompt.pack(side=tk.LEFT)

button_load_test_prompt = tk.Button(frame_input, text="Load Test Prompt", command=load_test_prompt, bg='orange')
button_load_test_prompt.pack(side=tk.LEFT)

# Label to display processed records count
processed_label = tk.Label(root, text="Processed Records: 0")
processed_label.pack(pady=5)

# Buttons to send queries to AI
button_test_first_10 = tk.Button(root, text="Test first 10 rows with AI",
                                 command=lambda: send_query_to_ai(row_limit=10), bg='lightgreen')
button_test_first_10.pack(pady=5)

button_send_query = tk.Button(root, text="Send entire dataset to AI", command=send_query_to_ai, bg='lightgreen')
button_send_query.pack(pady=10)

# Buttons for exporting data
button_export_tsv = tk.Button(root, text="Export Results as Tab-Delimited Text", command=export_to_tsv, bg='lightblue')
button_export_tsv.pack(pady=5)

button_export_xlsx = tk.Button(root, text="Export Results as Excel (XLSX)", command=export_to_xlsx, bg='lightblue')
button_export_xlsx.pack(pady=5)

# Help button
button_help = tk.Button(root, text="HELP", command=show_help, bg='orange')
button_help.pack(pady=5)

# Start the GUI event loop
root.mainloop()

print("FINAL RESULTS:", df)
