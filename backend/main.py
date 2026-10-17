from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Expo web dev server runs on a different origin than this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8081", "http://127.0.0.1:8081","http://localhost:8082"],
    allow_methods=["GET"],
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
                    "title": "Your experience, designed for you",
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
                            "label": "Favourite colour",
                            "options": ["Red", "Green", "Blue"],
                        },
                    },
                    {
                        "component": "PreferenceSelector",
                        "props": {
                            "label": "Theme",
                            "options": ["Light", "Dark"],
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
