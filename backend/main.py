import anthropic
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from layout_ai import LayoutGenerationError, NotConfiguredError, generate_layout

app = FastAPI()

# Expo web dev server runs on a different origin than this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081", "http://127.0.0.1:8081","http://localhost:8082"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Mirrors the LayoutConfig TypeScript type in src/adaptive/types.ts.
SERVER_LAYOUT = {
    "id": "server",
    "root": {
        "component": "Row",
        "props": {"direction": "column"},
        "children": [
            {
                "component": "WelcomeCard",
                "props": {
                    "title": "Today's training plan",
                    "message": "This layout was served by the backend.",
                },
            },
            {
                "component": "Row",
                "props": {"direction": "row", "breakpoint": 700},
                "children": [
                    {
                        "component": "PreferenceSelector",
                        "props": {
                            "label": "Workout length",
                            "options": ["15 min", "30 min", "45 min", "60 min"],
                        },
                    },
                    {
                        "component": "PreferenceSelector",
                        "props": {
                            "label": "Training place",
                            "options": ["Home", "Gym", "Outdoors"],
                        },
                    },
                ],
            },
        ],
    },
}


@app.get("/api/layout")
def get_layout():
    return SERVER_LAYOUT


class PersonalizeRequest(BaseModel):
    preference: str = Field(min_length=1, max_length=500)


@app.post("/api/layout/personalize")
def personalize_layout(request: PersonalizeRequest):
    try:
        return generate_layout(request.preference.strip())
    except NotConfiguredError:
        raise HTTPException(status_code=503, detail="Layout generation is not configured on the server")
    except LayoutGenerationError as error:
        raise HTTPException(status_code=502, detail=str(error))
    except anthropic.AnthropicError:
        # Don't leak SDK/auth details (or the key) to the client.
        raise HTTPException(status_code=502, detail="Layout generation service unavailable")
