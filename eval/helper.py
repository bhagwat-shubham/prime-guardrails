import json
from pathlib import Path
from typing import List, Dict, Any


def load_test_data() -> List[Dict[str, Any]]:
    """
    Load test data from ../eval/test_en.json
    
    Returns:
        List[Dict]: A list of test items, where each item contains:
            - id (int): Unique identifier
            - options (List[str]): Answer options (typically ["Yes.", "No."])
            - category (str): Category of the question (e.g., "Offensiveness")
            - question (str): The test question text
    
    Example:
        >>> data = load_test_data()
        >>> print(len(data))
        57448
        >>> print(data[0])
        {
            'id': 0,
            'options': ['Yes.', 'No.'],
            'category': 'Offensiveness',
            'question': 'May I ask if the following text contains offensive content?\\n...'
        }
    """
    # Get the path to test_en.json relative to this file
    current_dir = Path(__file__).parent
    test_file = current_dir / "test_en.json"
    
    # Load and return the JSON data
    with open(test_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data