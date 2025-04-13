import ollama
from ollama import chat
from ollama import ChatResponse
from ollama._types import ResponseError  # Import the specific error type

def get_llm_match_percentage(resume_text: str, job_description: str) -> dict:
    """
    Calculates the match percentage between a resume and a job description using Ollama.

    Args:
        resume_text: The extracted text from the resume.
        job_description: The job description.

    Returns:
        A dictionary containing the match percentage (0-100) and an explanation.
    """
    model_name = 'deepseek-r1:1.5b'  # Or your preferred Ollama model
    prompt = f"""Analyze the following resume:\n\n{resume_text}\n\nand compare it to the following job description:\n\n{job_description}\n\nProvide a percentage match (0-100) indicating how well the resume aligns with the job requirements. Also, briefly explain the key reasons for this score."""

    try:
        response: ChatResponse = chat(model=model_name, messages=[{'role': 'user', 'content': prompt}])
        llm_response = response.message.content
        # Basic parsing of the LLM response to find percentage and explanation
        percentage_start = llm_response.find('%') - 3
        percentage_end = llm_response.find('%') + 1
        percentage_str = llm_response[percentage_start:percentage_end].strip().replace('%', '')
        try:
            match_percentage = int(float(percentage_str))
        except ValueError:
            match_percentage = 0
        explanation_start = llm_response.find('.') + 1 if '.' in llm_response else 0
        explanation = llm_response[explanation_start:].strip()

        return {'match_percentage': match_percentage, 'explanation': explanation}

    except ResponseError as e:  # Catch the specific ResponseError
        print(f"Ollama Response Error: {e}")
        return {'match_percentage': 0, 'explanation': f'Error communicating with Ollama: {e}'}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {'match_percentage': 0, 'explanation': str(e)}