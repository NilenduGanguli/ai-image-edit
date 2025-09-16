"""
Handles all interactions with the Google Gemini AI, including:
1. Analyzing text to create editing prompts.
2. Editing images based on a prompt.
3. A utility function for testing image saving.
"""
import os
import uuid
import base64
from io import BytesIO
import requests
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- AI Configuration ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("Warning: GEMINI_API_KEY not found. AI services will be disabled.")

# Initialize the models synchronously
text_model = genai.GenerativeModel('gemini-1.5-flash-latest') if GEMINI_API_KEY else None
vision_model = genai.GenerativeModel('gemini-2.5-flash-image-preview') if GEMINI_API_KEY else None


def analyze_request(title: str, body: str = "") -> str:
    """
    Analyzes a Reddit post's title and body to generate a concise image editing prompt.
    This is a synchronous function.
    """
    if not text_model:
        return "AI model not configured. Please set GEMINI_API_KEY."

    prompt = f"""
    Analyze the following user request for an image edit. Your task is to create a concise, one-paragraph instruction for an AI image editor.
    Focus only on the technical editing requirements. Do not add any conversational fluff, greetings, or sign-offs.
    
    Examples:
    - "Remove the person in the background and enhance the colors."
    - "Change the color of the red car to a metallic blue."
    - "Restore this old, scratched photograph, fixing the cracks and improving the contrast."

    Post Title: "{title}"
    Post Body: "{body if body else 'No additional details provided.'}"

    AI Editing Prompt:
    """
    try:
        response = text_model.generate_content(prompt)
        # Clean up the response to ensure it's a single, clean paragraph
        analysis = response.text.strip().replace('"', '')
        return analysis
    except Exception as e:
        print(f"Error during Gemini text analysis: {e}")
        return f"Error analyzing request: {e}"


# def edit_image_with_gemini(image_url: str, prompt: str) -> dict:
#     """
#     Edits an image based on a prompt using the Gemini Vision model.
#     This is a synchronous function.
#     """
#     if not vision_model:
#         return {"ok": False, "error": "AI model not configured."}

#     try:
#         # 1. Download the image from the URL with a browser-like User-Agent
#         print(f"Downloading image from: {image_url}")
#         headers = {
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
#         }
#         with httpx.Client() as client:
#             response = client.get(image_url, headers=headers, timeout=30.0)
#             response.raise_for_status()
#             image_bytes = response.content

#         # 2. Verify and open the image with Pillow.
#         try:
#             image = Image.open(BytesIO(image_bytes))
#             image.verify() # Verify that this is a valid image file
#             # Re-open after verify
#             image = Image.open(BytesIO(image_bytes))
#             print(f"Image downloaded and verified successfully. Format: {image.format}, Mode: {image.mode}, Size: {image.size}")
#         except (IOError, SyntaxError) as e:
#             print(f"Error: Downloaded content is not a valid image. {e}")
#             return {"ok": False, "error": "The provided URL did not point to a valid image."}

#         # 3. Create a more direct prompt for the vision model
#         editing_prompt = f"""
#         **Task: Image Editing**

#         You are a professional photo editing AI. Your only task is to perform the following edit on the provided image and return the resulting image.
#         Do not describe the changes, do not add text, just output the edited image.

#         **Instruction:** "{prompt}"
#         """

#         # 4. Generate content with the vision model, passing the PIL image object.
#         print("Sending request to Gemini Vision API...")
#         generation_response = vision_model.generate_content([editing_prompt, image])
        
#         # 5. Extract the image data from the response
#         if generation_response.parts and hasattr(generation_response.parts[0], 'inline_data'):
#             generated_part = generation_response.parts[0]
#             image_data = generated_part.inline_data.data
#             output_mime_type = generated_part.inline_data.mime_type
            
#             image_base64 = base64.b64encode(image_data).decode('utf-8')
#             data_url = f"data:{output_mime_type};base64,{image_base64}"
            
#             print("Successfully received edited image from Gemini.")
#             return {
#                 "ok": True, 
#                 "edited_image_data": data_url
#             }
#         else:
#             error_message = "AI did not return an image. It may have refused the request due to safety policies or a vague prompt."
#             print(f"Error: {error_message}")
#             try:
#                 reason = generation_response.text
#                 error_message += f"\nReason: {reason}"
#             except Exception:
#                 pass
#             return {"ok": False, "error": error_message}

#     except httpx.RequestError as e:
#         print(f"Failed to download image: {e}")
#         return {"ok": False, "error": f"Failed to download image from URL: {e}"}
#     except Exception as e:
#         print(f"An error occurred during image editing: {e}")
#         return {"ok": False, "error": str(e)}
def edit_image_with_gemini(image_source: str, prompt: str) -> dict:
    """
    Edits an image based on a prompt using the Gemini Vision model.
    It can handle both remote URLs and local file paths.
    """
    if not vision_model:
        return {"ok": False, "error": "AI model not configured."}

    try:
        image_bytes = None
        # --- NEW LOGIC: Differentiate between URL and local path ---
        if image_source.startswith(('http://', 'https://')):
            # It's a URL, download it
            print(f"Downloading image from URL: {image_source}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(image_source, headers=headers, timeout=20)
            response.raise_for_status()
            image_bytes = response.content
        else:
            # It's a local path, read it from disk
            # We need to construct the full path relative to the current file
            # base_dir = os.path.dirname(os.path.abspath(__file__))
            # The path from JS will be like '/static/uploads/...', so we remove the leading '/'
            print(f"Loading image from local path: {image_source}")
            with open(image_source, "rb") as f:
                image_bytes = f.read()
        
        # Verify that we actually have image data
        if not image_bytes:
            raise ValueError("Could not load image data from source.")

        image = Image.open(BytesIO(image_bytes))
        print(f"Image loaded successfully. Format: {image.format}, Size: {image.size}")
        
        # A more direct prompt to ensure the AI returns an image
        final_prompt = f"""
        **Role**: You are an expert photo editing AI.
        **Task**: Follow the user's instructions precisely to edit the provided image.
        **Constraint**: Your response MUST be ONLY the edited image. Do not provide any text, descriptions, or commentary.

        **User's Instruction**: "{prompt}"
        """

        print("Sending request to Gemini Vision API...")
        generation_response = vision_model.generate_content([final_prompt, image])
        
        if generation_response.parts and generation_response.parts[0].inline_data:
            generated_part = generation_response.parts[0]
            image_data = generated_part.inline_data.data
            output_mime_type = generated_part.inline_data.mime_type
            
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            data_url = f"data:{output_mime_type};base64,{image_base64}"
            
            print("Successfully received edited image from Gemini.")
            return {"ok": True, "edited_image_data": data_url}
        else:
            error_message = "AI did not return an image. It may have refused the request due to safety policies or a vague prompt."
            try:
                reason = generation_response.text
                error_message += f"\nReason from AI: {reason}"
            except Exception:
                pass
            return {"ok": False, "error": error_message}

    except requests.exceptions.RequestException as e:
        return {"ok": False, "error": f"Failed to download image from URL: {e}"}
    except FileNotFoundError:
        return {"ok": False, "error": f"Image file not found at path: {image_source}"}
    except Exception as e:
        print(f"An error occurred during image editing: {e}")
        return {"ok": False, "error": str(e)}


def save_image_from_data_url(image_data_url: str, directory: str = "static/edited_images") -> str:
    """
    Decodes a base64 data URL and saves it as an image file.
    Returns the path to the saved file.
    """
    if not image_data_url or "base64," not in image_data_url:
        print("Invalid image data URL provided for saving.")
        raise ValueError("Invalid image data URL.")
        
    try:
        header, encoded = image_data_url.split(",", 1)
        image_bytes = base64.b64decode(encoded)
        image = Image.open(BytesIO(image_bytes))

        # Determine file extension
        mime_type = header.split(';')[0].split(':')[1]
        ext = 'png' if 'png' in mime_type else 'jpg'
        
        # Generate a unique filename
        file_name = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(directory, file_name)
        
        # Ensure the directory exists
        os.makedirs(directory, exist_ok=True)
        
        # Save the image
        image.save(file_path)
        print(f"Image saved to {file_path}")
        
        return file_path

    except Exception as e:
        print(f"An error occurred while saving the image: {e}")
        raise

# --- Test Block ---
if __name__ == '__main__':
    # To run this test:
    # 1. Set up your .env file with GEMINI_API_KEY
    # 2. Run `pip install -r requirements.txt`
    # 3. Run `python ai_service.py`

    def test_services():
        print("--- Testing AI Services (Synchronous) ---")
        if not GEMINI_API_KEY:
            print("\nGEMINI_API_KEY is not set. Cannot run tests.")
            return

        # --- Test 1: Text Analysis ---
        print("\n1. Testing Text Analysis (analyze_request)...")
        # test_title = "Please remove the plants in the foreground from this photo"
        # try:
        #     analysis = analyze_request(test_title)
        #     print(f"   - Analysis successful: {analysis}")
        # except Exception as e:
        #     print(f"   - Analysis failed: {e}")

        # --- Test 2: Image Editing ---
        print("\n2. Testing Image Editing (edit_image_with_gemini)...")
        test_image_url = "https://github.com/NilenduGanguli/usetest/blob/main/bootest.jpg?raw=true" # A simple, public image
        test_prompt = "make the leaves appear autumn colored"
        print(f"   - Using image: {test_image_url}")
        print(f"   - Using prompt: '{test_prompt}'")
        
        try:
            result = edit_image_with_gemini(test_image_url, test_prompt)
            if result.get("ok"):
                print("   - Image editing successful!")
                edited_image_data_url = result.get("edited_image_data")
                if edited_image_data_url:
                    save_image_from_data_url(edited_image_data_url, "temp/test_image_edit.png")
                else:
                    print("   - No image data returned in the successful response.")
            else:
                print(f"   - Image editing failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"   - An exception occurred during image editing: {e}")

    # test_services()

