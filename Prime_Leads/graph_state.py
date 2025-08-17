from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class GraphState(BaseModel):
    
    website_url: str
    
 
    GR_JSON: dict = Field(default_factory=dict)
    
    #
    ICP_GENERATOR_JSON: dict = Field(default_factory=dict)
    
 
    SEARCH_QUERY_JSON: dict = Field(default_factory=dict)
    
  
    pipeline_metadata: Optional[dict] = Field(default_factory=dict)
    
    class Config:
     
        extra = "allow"