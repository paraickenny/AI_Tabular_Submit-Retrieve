# GUI to read in tabular data, guide user to prepare AI prompt to interrogate data
# and write out the prompt for subsequent use with second application for batch
# submission of prompt with individual rows of data to LLM endpoint on Azure Cloud
# followed by retrieval of data

import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk, filedialog
import pandas as pd
import os


def load_file():
    global inputfile
    inputfile = filedialog.askopenfilename(
        title="Select a Tab-delimited Text or Excel File",
        filetypes=[("Text Files", "*.txt"), ("Excel Files", "*.xls *.xlsx")]
    )
    if inputfile:
        try:
            ext = os.path.splitext(inputfile)[1].lower()
            if ext == '.txt':
                df = pd.read_csv(inputfile, sep='\t', encoding='Windows-1252')  # Tab-delimited text
            elif ext in ['.xls', '.xlsx']:
                df = pd.read_excel(inputfile)  # Excel file
            else:
                messagebox.showerror("Error", "Unsupported file type selected.")
                return
            display_dataframe(df)
            show_explanation_fields()  # Show explanation fields after loading data
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")


def load_test_data():
    global inputfile
    inputfile = 'test_data.txt'
    try:
        df = pd.read_csv(inputfile, sep='\t')
        display_dataframe(df)
        show_explanation_fields()  # Show explanation fields after loading test data
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load test data: {e}")


def display_dataframe(df):
    # Clear previous content in the DataFrame display
    for widget in frame_data.winfo_children():
        widget.destroy()  # Clear previous content

    # Create a Treeview to display the DataFrame
    columns = list(df.columns)
    tree = ttk.Treeview(frame_data, columns=columns, show='headings')
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor='center')

    for index, row in df.iterrows():
        tree.insert("", "end", values=list(row))

    tree.pack(expand=True, fill='both')

    # Clear previous text boxes for explanation
    for widget in frame_explain.winfo_children():
        if isinstance(widget, tk.Frame):
            widget.destroy()  # Clear previous text boxes

    global input_fields_dict
    input_fields_dict = {}

    # Create text boxes for each column header
    for column in df.columns:
        frame_row = tk.Frame(frame_explain)
        frame_row.pack(pady=2)

        label = tk.Label(frame_row, text=column)
        label.pack(side=tk.LEFT)

        text_box = tk.Entry(frame_row, width=80)
        text_box.insert(0, column)  # Initialize with column header
        text_box.pack(side=tk.LEFT)

        input_fields_dict[column] = text_box


def show_explanation_fields():
    frame_explain.pack(pady=10)  # Show the explanation frame


def data_explanation_complete():
    explanation_dict = {label: entry.get() for label, entry in input_fields_dict.items()}
    print(explanation_dict)  # You can process this dictionary as needed


def store_role():
    global role
    role = entry_role.get()
    print(f"Role stored: {role}")  # You can process this variable as needed


def store_problem():
    global problem
    problem = entry_problem.get("1.0", tk.END).strip()  # Get text from the text area
    print(f"Problem stored: {problem}")  # You can process this variable as needed


def finalize_output_fields():
    global output_fields_dict
    output_fields_dict = {}
    for i in range(6):
        field_name = entry_field_names[i].get().strip()
        description = entry_descriptions[i].get().strip()
        if field_name and description:  # Only store if both are not empty
            output_fields_dict[field_name] = description
    print(output_fields_dict)  # You can process this dictionary as needed
    assemble_prompt()


def assemble_prompt():
    global assembled_prompt
    global role, problem, input_fields_dict, output_fields_dict  # Declare as global
    x = len(input_fields_dict)
    assembled_prompt = f"You will act as a {role}\n"
    assembled_prompt += f"I will provide a row of tab-delimited data containing {x} elements, with the following field names and descriptions:\n"

    for k, v in input_fields_dict.items():
        assembled_prompt += f"{k}: {v.get()}\n"

    assembled_prompt += f"The problem I would like you to address is:\n{problem}\n"
    assembled_prompt += "Analyze these data and report the following items in JSON format. Do not add any additional text or commentary:\n"

    # Add the line for output fields
    output_fields_list = ', '.join(output_fields_dict.keys())
    assembled_prompt += f"Output_Fields will be [{output_fields_list}]\n"

    for k, v in output_fields_dict.items():
        assembled_prompt += f"{k}: {v}\n"

    assembled_prompt += "Here are the data:\n"

    text_assembled_prompt.config(state='normal')  # Enable editing to update the text
    text_assembled_prompt.delete(1.0, tk.END)  # Clear previous content
    text_assembled_prompt.insert(tk.END, assembled_prompt)  # Display assembled prompt
    text_assembled_prompt.config(state='disabled')  # Make it non-editable again


def save_prompt():
    filename = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
    if filename:
        with open(filename, "w", encoding="utf-8") as file:  # Specify UTF-8 encoding
            file.write(assembled_prompt)
        messagebox.showinfo("Success", f"Prompt saved as {filename}")


def on_button_click(button):
    button.config(bg='lightgreen')


def show_help():
    help_text = (
        "Tab-delimited text data can be imported with the load buttons. "
        "Then Provide any detailed explanations so that the AI will understand your data fields. "
        "Guide the AI's analysis strategy by suggesting the role of a human who might normally perform this analysis. "
        "Describe the problem you want the AI to solve in detail. "
        "Then specify the output fields that you want the AI to capture, providing a detailed explanation for each one. "
        "If formatting of the output data is important e.g. 'Grade should be displayed as a number' or 'Date should be shown as DDMMYY' "
        "then specify that in the 'Detailed Description' boxes. "
        "Clicking 'Finalize Output Fields' will display the complete prompt. This can then be saved as a txt file and imported into the batch query submitter app. "
        "Problems? Contact Paraic Kenny pakenny@gundersenhealth.org."
    )
    messagebox.showinfo("Help", help_text)


# Create main window
root = tk.Tk()
root.title("AI Batch Query Prompt Engineering Tool")
root.geometry("1600x1000")  # Set initial size of the GUI

# Create a scrollable frame
scrollable_frame = tk.Frame(root)
scrollable_frame.pack(expand=True, fill='both')

canvas = tk.Canvas(scrollable_frame)
scrollbar = tk.Scrollbar(scrollable_frame, orient="vertical", command=canvas.yview, width=50)  # Set scrollbar width
scrollable_content = tk.Frame(canvas)

scrollable_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
canvas.create_window((0, 0), window=scrollable_content, anchor="nw")

canvas.configure(yscrollcommand=scrollbar.set)


# Bind mouse wheel scrolling
def on_mouse_wheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


canvas.bind_all("<MouseWheel>", on_mouse_wheel)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Help button
button_help = tk.Button(scrollable_content, text="Help", command=show_help, bg='orange')
button_help.pack(side=tk.TOP, anchor='nw', padx=10, pady=10)

# Input file section
frame_input = tk.Frame(scrollable_content)
frame_input.pack(pady=10)

button_load = tk.Button(frame_input, text="Load Tab-Delimited Text or Excel data",
                        command=lambda: [load_file(), on_button_click(button_load)], bg='orange')
button_load.pack(side=tk.LEFT)

button_load_test = tk.Button(frame_input, text="Load test data",
                             command=lambda: [load_test_data(), on_button_click(button_load_test)], bg='orange')
button_load_test.pack(side=tk.LEFT)

# Frame for displaying DataFrame
frame_data = tk.Frame(scrollable_content)
frame_data.pack(pady=10, fill='both', expand=True)

# Explain your data section
frame_explain = tk.Frame(scrollable_content)
frame_explain.pack(pady=10)  # Pack this frame immediately below the DataFrame display

label_explain = tk.Label(frame_explain, text="Explain your data fields to me:")
label_explain.pack(side=tk.LEFT)

# Button to complete data explanation
button_complete = tk.Button(frame_explain, text="Data Explanation Complete",
                            command=lambda: [data_explanation_complete(), on_button_click(button_complete)],
                            bg='orange')
button_complete.pack(side=tk.LEFT, padx=(10, 0))

# Role input section
frame_role = tk.Frame(scrollable_content)
frame_role.pack(pady=10)

label_role = tk.Label(frame_role,
                      text="Enter the role you would like the AI system to play e.g. Pathologist, Cancer Registrar etc.:")
label_role.pack(side=tk.LEFT)

entry_role = tk.Entry(frame_role, width=50)
entry_role.pack(side=tk.LEFT)

button_store_role = tk.Button(frame_role, text="Store Role",
                              command=lambda: [store_role(), on_button_click(button_store_role)], bg='orange')
button_store_role.pack(side=tk.LEFT)

# Problem input section
frame_problem = tk.Frame(scrollable_content)
frame_problem.pack(pady=10)

label_problem = tk.Label(frame_problem,
                         text="Describe the general problem you want the AI system to solve for each row of your dataset:")
label_problem.pack()

entry_problem = scrolledtext.ScrolledText(frame_problem, width=120, height=8, wrap=tk.WORD)
entry_problem.pack()

button_store_problem = tk.Button(frame_problem, text="Store Problem",
                                 command=lambda: [store_problem(), on_button_click(button_store_problem)], bg='orange')
button_store_problem.pack()

# New section for output fields
label_output_fields = tk.Label(scrollable_content, text="Describe the information you want the AI tool to capture:")
label_output_fields.pack(pady=10)

frame_output_fields = tk.Frame(scrollable_content)
frame_output_fields.pack(pady=10)

entry_field_names = []
entry_descriptions = []

for i in range(6):
    frame_row = tk.Frame(frame_output_fields)
    frame_row.pack(pady=2)

    label_field_name = tk.Label(frame_row, text="Field Name:")
    label_field_name.pack(side=tk.LEFT)

    entry_field_name = tk.Entry(frame_row, width=50)
    entry_field_name.pack(side=tk.LEFT)
    entry_field_names.append(entry_field_name)

    label_description = tk.Label(frame_row, text="Detailed description:")
    label_description.pack(side=tk.LEFT)

    entry_description = tk.Entry(frame_row, width=200)
    entry_description.pack(side=tk.LEFT)
    entry_descriptions.append(entry_description)

button_finalize_output_fields = tk.Button(scrollable_content, text="Finalize Output Fields",
                                          command=lambda: [finalize_output_fields(),
                                                           on_button_click(button_finalize_output_fields)], bg='orange')
button_finalize_output_fields.pack(pady=10)

# Assembled Prompt section
label_assembled_prompt = tk.Label(scrollable_content, text="Assembled Prompt:")
label_assembled_prompt.pack(pady=10)

text_assembled_prompt = scrolledtext.ScrolledText(scrollable_content, width=200, height=15, wrap=tk.WORD,
                                                  state='normal')
text_assembled_prompt.pack(pady=10)
text_assembled_prompt.config(state='disabled')  # Make it non-editable

# Save Prompt section
button_save_prompt = tk.Button(scrollable_content, text="Save Prompt as .txt file", command=save_prompt, bg='orange')
button_save_prompt.pack(pady=10)

# Initialize global variables
role = ""
problem = ""
input_fields_dict = {}
output_fields_dict = {}
assembled_prompt = ""

# Start the GUI event loop
root.mainloop()
