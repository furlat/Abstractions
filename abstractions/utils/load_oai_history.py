import json

def load_first_record(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        if isinstance(data, list) and len(data) > 0:
            return data[0]  # Return the first item in the list
        else:
            raise ValueError("JSON is not a list or is empty")

def load_nth_record(file_path, n):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        if isinstance(data, list) and len(data) > n:
            return data[n]  # Return the nth item in the list
        else:
            raise ValueError("JSON is not a list or does not have enough items")
        
def load_all_records(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        if isinstance(data, list):
            return data  # Return the whole list
        else:
            raise ValueError("JSON is not a list")