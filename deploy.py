import vertexai
from vertexai import agent_engines
from vertexai.preview import reasoning_engines
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Configuration ---
# Load from environment variables, with placeholders for the user to fill in.
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "<YOUR_PROJECT_ID>")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
STAGING_BUCKET = "gs://<YOUR_STAGING_BUCKET_NAME>"
DEPLOY_DISPLAY_NAME = "Google Drive ACL Agent"

# Environment variables for the deployed agent.
# Note: GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are set automatically
# in the deployment environment and should not be passed explicitly.
DEPLOY_ENVIRONMENT = {
    "GOOGLE_GENAI_USE_VERTEXAI": os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True"),
}

# --- Main Deployment Logic ---

# Import the agent defined in agent.py
try:
    from agent import root_agent
    print("Successfully imported 'root_agent' from agent.py")
except ImportError as e:
    print(f"Error: Could not import 'root_agent'. Error: {e}")
    exit()

# Read requirements from requirements.txt
try:
    with open("requirements.txt", "r") as f:
        requirements = [line.strip() for line in f if line.strip()]
    print(f"Found requirements: {requirements}")
except FileNotFoundError:
    print("Error: requirements.txt not found.")
    exit()

# Initialize Vertex AI SDK
print(f"Initializing Vertex AI for project '{PROJECT_ID}' in '{LOCATION}' with staging bucket '{STAGING_BUCKET}'...")
vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

# Wrap the agent in an AdkApp
print("Creating AdkApp...")
app = reasoning_engines.AdkApp(
    agent=root_agent,
    enable_tracing=True,
)

# List of files to package for deployment
extra_packages = ["agent.py"]
print(f"Packaging extra files: {extra_packages}")

# Deploy the agent
print(f"Deploying Agent Engine with display name: '{DEPLOY_DISPLAY_NAME}'")
remote_app = agent_engines.create(
    display_name=DEPLOY_DISPLAY_NAME,
    agent_engine=app,
    requirements=requirements,
    extra_packages=extra_packages,
    description="An agent that can list files in Google Drive, requiring user authorization.",
    env_vars=DEPLOY_ENVIRONMENT
)

print("\n" + "="*60)
print("Deployment submitted successfully!")
print("Please wait a few minutes for the deployment to complete.")
print(f"The Reasoning Engine resource name is: {remote_app.resource_name}")
print("You will need the ID part of this name for the final registration step.")
print("="*60 + "\n")

try:
    deployment_id = remote_app.resource_name.split('/')[-1]
    print(f"Extracted ADK_DEPLOYMENT_ID: {deployment_id}")
except Exception as e:
    print(f"Could not automatically extract deployment ID. Please copy it from the resource name above. Error: {e}")
