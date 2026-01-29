"""Schemas for Chotu chat agent endpoint"""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request schema for chat query"""
    user_id: str = Field(..., alias="userId", description="User ID making the query")
    message: str = Field(..., description="User's natural language question")
    
    class Config:
        populate_by_name = True


class QueryResponse(BaseModel):
    """Response schema for chat query"""
    answer: str = Field(..., description="Natural language answer to the query")
    confidence: float = Field(..., description="Confidence score between 0 and 1")
    query: str = Field(default="", description="SQL query executed")
    
    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    """Error response schema"""
    error: str = Field(..., description="Error message")
    detail: str = Field(default="", description="Detailed error information")
