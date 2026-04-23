import re
from fastapi import FastAPI, Request, Response, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from core.error_handlers import register_error_handlers, validation_error_handler
from core.exceptions import BadRequestException, UnprocessableException
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from functools import lru_cache
from core import config
from contextlib import asynccontextmanager
from config.database import collection
from config.model import create_profile_list_item
from typing import Annotated, Literal
import pymongo


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.limiter = limiter
    yield


limiter = Limiter(key_func=get_remote_address)
app = FastAPI(lifespan=lifespan, title="Demographic Intelligence API")
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


_COUNTRY_NAME_TO_ISO: dict[str, str] = {
    "nigeria": "NG", "nigerian": "NG", "nigerians": "NG",
    "ghana": "GH", "ghanaian": "GH", "ghanaians": "GH",
    "kenya": "KE", "kenyan": "KE", "kenyans": "KE",
    "south africa": "ZA", "south african": "ZA", "south africans": "ZA",
    "angola": "AO", "angolan": "AO", "angolans": "AO",
    "benin": "BJ", "beninese": "BJ",
    "ethiopia": "ET", "ethiopian": "ET", "ethiopians": "ET",
    "tanzania": "TZ", "tanzanian": "TZ", "tanzanians": "TZ",
    "uganda": "UG", "ugandan": "UG", "ugandans": "UG",
    "cameroon": "CM", "cameroonian": "CM", "cameroonians": "CM",
    "senegal": "SN", "senegalese": "SN",
    "ivory coast": "CI", "cote d'ivoire": "CI", "cote divoire": "CI",
    "mozambique": "MZ", "mozambican": "MZ",
    "zambia": "ZM", "zambian": "ZM",
    "zimbabwe": "ZW", "zimbabwean": "ZW",
    "mali": "ML", "malian": "ML",
    "niger": "NE", "nigerien": "NE",
    "guinea": "GN", "guinean": "GN",
    "rwanda": "RW", "rwandan": "RW",
    "somalia": "SO", "somali": "SO",
    "malawi": "MW", "malawian": "MW",
    "burkina faso": "BF", "burkinabe": "BF",
    "togo": "TG", "togolese": "TG",
    "sierra leone": "SL",
    "liberia": "LR", "liberian": "LR",
    "botswana": "BW",
    "namibia": "NA", "namibian": "NA",
    "mauritius": "MU",
    "mauritania": "MR", "mauritanian": "MR",
    "gabon": "GA", "gabonese": "GA",
    "congo": "CG", "congolese": "CG",
    "dr congo": "CD", "democratic republic of congo": "CD",
    "chad": "TD", "chadian": "TD",
    "sudan": "SD", "sudanese": "SD",
    "egypt": "EG", "egyptian": "EG",
    "morocco": "MA", "moroccan": "MA",
    "tunisia": "TN", "tunisian": "TN",
    "algeria": "DZ", "algerian": "DZ",
    "libya": "LY", "libyan": "LY",
    "madagascar": "MG", "malagasy": "MG",
    "lesotho": "LS",
    "eswatini": "SZ", "swaziland": "SZ",
    "eritrea": "ER", "eritrean": "ER",
    "djibouti": "DJ",
    "south sudan": "SS",
    "central african republic": "CF",
    "cape verde": "CV",
    "equatorial guinea": "GQ",
    "seychelles": "SC",
    "comoros": "KM",
    "united states": "US", "usa": "US", "america": "US", "american": "US",
    "united kingdom": "GB", "uk": "GB", "britain": "GB", "british": "GB",
    "france": "FR", "french": "FR",
    "germany": "DE", "german": "DE",
    "spain": "ES", "spanish": "ES",
    "italy": "IT", "italian": "IT",
    "portugal": "PT", "portuguese": "PT",
    "brazil": "BR", "brazilian": "BR",
    "india": "IN", "indian": "IN",
    "china": "CN", "chinese": "CN",
    "japan": "JP", "japanese": "JP",
    "canada": "CA", "canadian": "CA",
    "australia": "AU", "australian": "AU",
    "netherlands": "NL", "dutch": "NL",
    "sweden": "SE", "swedish": "SE",
    "norway": "NO", "norwegian": "NO",
    "denmark": "DK", "danish": "DK",
    "finland": "FI", "finnish": "FI",
    "poland": "PL", "polish": "PL",
    "russia": "RU", "russian": "RU",
    "turkey": "TR", "turkish": "TR",
    "mexico": "MX", "mexican": "MX",
    "argentina": "AR", "argentinian": "AR",
    "colombia": "CO", "colombian": "CO",
    "chile": "CL", "chilean": "CL",
    "peru": "PE", "peruvian": "PE",
    "venezuela": "VE", "venezuelan": "VE",
    "indonesia": "ID", "indonesian": "ID",
    "philippines": "PH", "filipino": "PH",
    "vietnam": "VN", "vietnamese": "VN",
    "thailand": "TH", "thai": "TH",
    "malaysia": "MY", "malaysian": "MY",
    "pakistan": "PK", "pakistani": "PK",
    "bangladesh": "BD", "bangladeshi": "BD",
    "south korea": "KR", "korean": "KR",
    "iran": "IR", "iranian": "IR",
    "iraq": "IQ", "iraqi": "IQ",
    "saudi arabia": "SA", "saudi": "SA",
    "new zealand": "NZ",
}

_AGE_STOPPERS = r"above|below|over|under|at\s+least|more\s+than|less\s+than|aged?|who|with"


def _extract_country(q_lower: str) -> str | None:
    """Extract everything after 'from'/'in', strip trailing stoppers, return raw text."""
    m = re.search(r'\b(?:from|in)\s+(.+?)(?=\s+(?:' + _AGE_STOPPERS + r')|\s*$)', q_lower)
    if not m:
        return None
    return m.group(1).strip()


def _parse_nl_query(q: str) -> dict | None:
    """
    Converts a plain-English query string into a MongoDB filter dict.
    Returns None when no recognisable pattern is found.
    """
    q_lower = q.lower().strip()
    query: dict = {}
    recognized = False

    has_male = bool(re.search(r'\b(males?|men|man|boys?)\b', q_lower))
    has_female = bool(re.search(r'\b(females?|women|woman|girls?)\b', q_lower))
    if has_male and not has_female:
        query["gender"] = "male"
        recognized = True
    elif has_female and not has_male:
        query["gender"] = "female"
        recognized = True
    elif has_male and has_female:
        recognized = True

    if re.search(r'\b(children|child|kids?)\b', q_lower):
        query["age_group"] = "child"
        recognized = True
    elif re.search(r'\b(teenagers?|teens?|adolescents?)\b', q_lower):
        query["age_group"] = "teenager"
        recognized = True
    elif re.search(r'\b(adults?)\b', q_lower):
        query["age_group"] = "adult"
        recognized = True
    elif re.search(r'\b(seniors?|elderly)\b', q_lower):
        query["age_group"] = "senior"
        recognized = True

    if re.search(r'\b(young|youth)\b', q_lower) and "age_group" not in query:
        query.setdefault("age", {})
        query["age"]["$gte"] = 16
        query["age"]["$lte"] = 24
        recognized = True

    above = re.search(r'\b(?:above|over|older than|at least|more than)\s+(\d+)', q_lower)
    if above:
        query.setdefault("age", {})
        query["age"]["$gte"] = int(above.group(1))
        recognized = True

    below = re.search(r'\b(?:below|under|younger than|at most|less than)\s+(\d+)', q_lower)
    if below:
        query.setdefault("age", {})
        query["age"]["$lte"] = int(below.group(1))
        recognized = True

    between = re.search(r'\bbetween\s+(\d+)\s+and\s+(\d+)', q_lower)
    if between:
        query["age"] = {"$gte": int(between.group(1)), "$lte": int(between.group(2))}
        recognized = True

    country_text = _extract_country(q_lower)
    if country_text:
        iso = None
        for name in sorted(_COUNTRY_NAME_TO_ISO, key=len, reverse=True):
            if country_text == name or country_text.startswith(name):
                iso = _COUNTRY_NAME_TO_ISO[name]
                break
        if iso:
            query["country_id"] = iso
        else:
            query["country_name"] = {"$regex": re.escape(country_text), "$options": "i"}
        recognized = True

    return query if recognized else None


@app.get("/")
async def home():
    return JSONResponse(content={
        "status": "success",
        "message": {
            "title": "Demographic Intelligence API",
            "about": "A RESTful API for querying and analyzing demographic profiles by gender, age, and nationality.",
        }
    }, status_code=200)


@app.get("/health")
async def health_check():
    return JSONResponse(content={"status": "success", "message": "Ok"}, status_code=200)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/api/profiles/search")
async def search_profiles(
    request: Request,
    q: str | None = Query(default=None),
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    if not q or not q.strip():
        raise BadRequestException("Missing or empty parameter")

    parsed = _parse_nl_query(q.strip())
    if parsed is None:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Unable to interpret query"},
        )

    skip = (page - 1) * limit
    total = collection.count_documents(parsed)
    docs = list(
        collection.find(parsed)
        .sort([("created_at", pymongo.DESCENDING)])
        .skip(skip)
        .limit(limit)
    )

    return JSONResponse(content={
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [create_profile_list_item(d) for d in docs],
    }, status_code=200)


@limiter.limit("8/minute")
@app.get("/api/profiles")
async def fetch_profiles(
    request: Request,
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
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
):
    query: dict = {}

    if gender:
        query["gender"] = gender.lower()
    if age_group:
        query["age_group"] = age_group.lower()
    if country_id:
        query["country_id"] = country_id.upper()

    age_filter: dict = {}
    if min_age is not None:
        age_filter["$gte"] = min_age
    if max_age is not None:
        age_filter["$lte"] = max_age
    if age_filter:
        query["age"] = age_filter

    if min_gender_probability is not None:
        query["gender_probability"] = {"$gte": min_gender_probability}
    if min_country_probability is not None:
        query["country_probability"] = {"$gte": min_country_probability}

    sort_field = (sort_by or "created_at").lower()
    sort_dir = pymongo.DESCENDING if (order or "").lower() == "desc" else pymongo.ASCENDING
    sort_spec = [(sort_field, sort_dir)]
    
    if sort_field != "created_at":
        sort_spec.append(("created_at", pymongo.DESCENDING))

    skip = (page - 1) * limit
    total = collection.count_documents(query)
    docs = list(
        collection.find(query)
        .sort(sort_spec)
        .skip(skip)
        .limit(limit)
    )

    return JSONResponse(content={
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [create_profile_list_item(d) for d in docs],
    }, status_code=200)
