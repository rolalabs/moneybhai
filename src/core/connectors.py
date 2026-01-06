from google import genai
from google.genai.types import HttpOptions
from src.core.environment import ENV_SETTINGS


GEN_AI_CLIENT = genai.Client(api_key=ENV_SETTINGS.GEMINI_API_KEY, http_options=HttpOptions(timeout=60))

# Initialize the Gemini model
# MODEL = outlines.from_gemini(GEN_AI_CLIENT, "gemini-2.5-flash")


# credentials = service_account.Credentials.from_service_account_info(
#     json.loads(ENV_SETTINGS.GOOGLE_APPLICATION_CREDENTIALS)
# )
# credentials = credentials.with_scopes(["https://www.googleapis.com/auth/cloud-platform"])
