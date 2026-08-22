"""
PJECZ Hercules Beta Flask
"""

import os

from dotenv import load_dotenv

load_dotenv()
FLASK_APP = os.getenv("FLASK_APP", "pjecz_hercules_beta_flask.app") + ":create_app"
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1")

if __name__ == "__main__":
    """Main function to run the Flask application."""
    from uvicorn import run as uvicorn_run
    uvicorn_run(FLASK_APP, host=FLASK_HOST, port=FLASK_PORT, reload=FLASK_DEBUG == "1")
