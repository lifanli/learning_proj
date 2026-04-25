from src.webapi.app import FRONTEND_DIST, app

if __name__ == "__main__":
    import os

    import uvicorn

    host = os.getenv("STUDY_PROJ_HOST", "127.0.0.1")
    port = int(os.getenv("STUDY_PROJ_PORT", "8000"))
    display_host = "localhost" if host in {"0.0.0.0", "::"} else host
    url = f"http://{display_host}:{port}"

    if (FRONTEND_DIST / "index.html").is_file():
        print(f"Serving API and Vue frontend at {url}")
    else:
        print("Serving API only. Build the frontend with: cd frontend && npm run build")
    uvicorn.run(app, host=host, port=port)
