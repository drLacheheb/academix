from typing import Optional, List
from pydantic import BaseModel


class JobStubCreate(BaseModel):
    title: str
    url: str
    source: str


class JobDetailUpdate(BaseModel):
    url: str
    description: Optional[str] = None
    requirements: Optional[str] = None
    deadline: Optional[str] = None
    employer: Optional[str] = None
    location: Optional[str] = None


class RefinementResult(BaseModel):
    url: str
    required_skills: List[str]
    education_level: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None



class ClaimRequest(BaseModel):
    agent_name: str


class KnownUrlsRequest(BaseModel):
    urls: List[str]


class DetectionResult(BaseModel):
    url: str
    language_code: str


class TranslationResult(BaseModel):
    url: str
    description_en: Optional[str] = None
    requirements_en: Optional[str] = None

