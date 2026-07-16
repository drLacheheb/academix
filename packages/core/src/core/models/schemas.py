from typing import Optional, List
from pydantic import BaseModel


class JobStubCreate(BaseModel):
    title: str
    url: str
    source: str
    keywords: List[str] = []


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


class ClaimRequest(BaseModel):
    agent_name: str


class KnownUrlsRequest(BaseModel):
    urls: List[str]
