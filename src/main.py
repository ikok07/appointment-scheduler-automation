from dotenv import load_dotenv

from src.lifespan import lifespan

load_dotenv()

from fastapi import FastAPI
from starlette import status
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.models.errors.api import APIError
from src.routes.versions import v1_routes

app = FastAPI(lifespan=lifespan)

app.include_router(v1_routes.router, prefix="/api/v1", tags=["V1"])

@app.exception_handler(APIError)
async def api_error_handler(req: Request, err: APIError):
    """ Handle all errors during api route handlers """
    return JSONResponse(
        status_code=err.status_code,
        content={"error": err.message}
    )

@app.exception_handler(Exception)
async def generic_error_handler(req: Request, err: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": str(err)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)