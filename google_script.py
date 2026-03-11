from google import genai
import os

# Create client
client = genai.Client(api_key="AIzaSyCBJXgOhGExj4WQVwfzGwt3N76O8x1ru8w")

# Prompt
prompt = "Explain in simple terms how Large Language Models work."
print(prompt)
# Call Gemini 2.5 Pro
response = client.models.generate_content(
    model="gemini-2.5-pro",
    contents=prompt
)
print(response)
# Print result
print(response.text)