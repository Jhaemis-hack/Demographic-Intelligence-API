import re
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from core.error_handlers import register_error_handlers, validation_error_handler
from core.exceptions import NotFoundException, BadRequestException, UnprocessableException
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from functools import lru_cache
from core import config
from contextlib import asynccontextmanager
from config.database import collection
from config.model import create_profile, create_profile_list_item
from typing import Annotated
from typing import Literal
import pymongo

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.limiter = limiter
    yield


limiter = Limiter(key_func=get_remote_address)

app = FastAPI(lifespan=lifespan, title="Classification App")
register_error_handlers(app)

app.add_exception_handler(RequestValidationError, validation_error_handler)
app.add_exception_handler(RateLimitExceeded, lambda request, exc: JSONResponse(
    status_code=429,
    content={"status": "error", "message": "Too many requests, please slow down."},
))


@lru_cache
def get_settings():
    return config.Settings()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home():
    return JSONResponse(content={
        "status": "success",
        "message": {
            "title": "Classification App",
            "about": "A RESTful API that predicts gender, age, and nationality from a name.",
        }
    }, status_code=200)


@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "success", "message": "Ok"}, status_code=200)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@limiter.limit("8/minute")
@app.get("/api/profiles")
async def fetch_profiles(request: Request, 
    gender: Literal["male", "Male", "MALE", "Female", "FEMALE", "female"] | None = Query(default=None),
    age_group: str | None = Query(default=None),
    country_id: str | None = Query(default=None),
    min_age: int | None = Query(default=None),
    max_age: int | None = Query(default=None),
    min_gender_probability: float | None = Query(default=None),
    min_country_probability: float | None = Query(default=None),
    order: Literal["asc", "ASC", "DESC", "Asc", "Desc", "desc"] | None = Query(default=None),
    sort_by: Literal["age", "created_at", "gender_probability"] | None = Query(default=None),
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=10, le=50)] = 10,
    ):
    
    query = {}
    
    if gender:
        query["gender"] = gender.lower()
    if age_group:
        query["age_group"] = age_group.lower()
    if country_id:
        query["country_id"] = country_id.upper()
    if min_age:
        query["age"] = { "$gte": min_age }
    if max_age:
        query["age"] = { "$lte": max_age }
    if min_gender_probability:
        query["gender_probability"] =  { "$gte": min_gender_probability }
    if min_country_probability:
        query["country_probability"] = { "$gte": min_country_probability }

    sort = {
        "sort_by": sort_by.lower() if sort_by else "",
        "order": order.lower() if order else "",
    }

    total_docs = list(collection.find(query).sort([ sort["sort_by"], ("created_at", pymongo.DESCENDING if sort["order"] == "desc" else pymongo.DESCENDING)]))
    docs = list(collection.find(query).sort([ sort["sort_by"], ("created_at", pymongo.DESCENDING if sort["order"] == "desc" else pymongo.DESCENDING)]).limit(limit=limit).skip(skip=(page * (limit) - limit)))
        
    return JSONResponse(content={
        "status": "success",
        "page": page,
        "limit": limit,
        "total": len(total_docs),
        "data": [create_profile_list_item(d) for d in docs],
    }, status_code=200)
    


@app.get("/api/profiles/search")
async def natural_language_query(
    request: Request,
    q: str | None = Query(default=None)
    ):
    
    if not q:
        raise BadRequestException("Missing or empty parameter")
    
    parsed_query = re.sub(r'[^a-zA-Z]', '', q).lower()
    
    if not parsed_query:
        raise UnprocessableException("Invalid parameter type")
    
    doc = collection.find_one({"id": ""})
    
    if not doc:
        raise NotFoundException("Profile not found")
    
    return JSONResponse(content={
        "status": "success",
        "data": create_profile(doc),
    }, status_code=200)
