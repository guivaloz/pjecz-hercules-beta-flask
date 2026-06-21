"""
Programa principal
"""

import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()
FLASK_APP = os.getenv("FLASK_APP", "pjecz_hercules_beta_flask.app") + ":app"
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

if __name__ == "__main__":
    uvicorn.run(FLASK_APP, host=FLASK_HOST, port=FLASK_PORT, reload=True)
